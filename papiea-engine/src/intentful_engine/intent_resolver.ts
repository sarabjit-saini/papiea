import { Spec_DB } from "../databases/spec_db_interface";
import { Status_DB } from "../databases/status_db_interface";
import { IntentWatcher_DB } from "../databases/intent_watcher_db_interface";
import { Provider_DB } from "../databases/provider_db_interface";
import { Handler, IntentfulListener } from "./intentful_listener_interface";
import { EntryReference, Watchlist } from "./watchlist";
import { IntentfulStatus, Diff, Differ, Entity, IntentWatcher } from "papiea-core";
import * as assert from "assert";
import { timeout } from "../utils/utils";
import { DiffResolver } from "./diff_resolver";
import { Logger } from "papiea-backend-utils";
import deepEqual = require("deep-equal");

export class IntentResolver {
    private readonly specDb: Spec_DB
    private readonly statusDb: Status_DB
    private readonly intentWatcherDb: IntentWatcher_DB
    private readonly providerDb: Provider_DB

    private intentfulListener: IntentfulListener
    private differ: Differ
    private diffResolver: DiffResolver;
    private logger: Logger;
    private watchlist: Watchlist;

    constructor(specDb: Spec_DB, statusDb: Status_DB,
                intentWatcherDb: IntentWatcher_DB, providerDb: Provider_DB,
                intentfulListener: IntentfulListener, differ: Differ,
                diffResolver: DiffResolver, watchlist: Watchlist,
                logger: Logger)
    {
        this.specDb = specDb
        this.statusDb = statusDb
        this.providerDb = providerDb
        this.intentWatcherDb = intentWatcherDb
        this.logger = logger

        this.onChange = this.onChange.bind(this)
        this.onIntentfulHandlerFail = this.onIntentfulHandlerFail.bind(this)

        this.watchlist = watchlist
        this.diffResolver = diffResolver
        this.differ = differ
        this.intentfulListener = intentfulListener
        this.intentfulListener.onChange = new Handler(this.onChange)
        this.diffResolver.onIntentfulHandlerFail = new Handler(this.onIntentfulHandlerFail)
    }

    private static getIntersection(current_diffs: Diff[], watcher_diffs: Diff[], predicate: (curr_diff: Diff, watcher_diff: Diff) => boolean): Set<Diff> {
        const intersection: Set<Diff> = new Set()
        for (let diff of current_diffs) {
            for (let watcher_diff of watcher_diffs) {
                if (predicate(diff, watcher_diff)) {
                    intersection.add(diff)
                }
            }
        }
        return intersection
    }

    private static inTerminalState(watcher: IntentWatcher): boolean {
        const terminal_states = [IntentfulStatus.Completed_Partially, IntentfulStatus.Completed_Successfully, IntentfulStatus.Outdated, IntentfulStatus.Failed]
        return terminal_states.includes(watcher.status)
    }

    private async clearTerminalStateWatchers(watcherExpirySeconds: number) {
        const watchers = await this.intentWatcherDb.list_watchers({})
        for (let watcher of watchers) {
            if (IntentResolver.inTerminalState(watcher)) {
                if (watcher.last_status_changed && (new Date().getTime() - watcher.last_status_changed.getTime()) / 1000 > watcherExpirySeconds) {
                    await this.intentWatcherDb.delete_watcher(watcher.uuid)
                }
            }
        }
    }

    private async rediff(entity: Entity): Promise<Diff[]> {
        const provider = await this.providerDb.get_provider(entity.metadata.provider_prefix, entity.metadata.provider_version)
        const kind = this.providerDb.find_kind(provider, entity.metadata.kind)
        return this.differ.all_diffs(kind, entity.spec, entity.status)
    }

    private async processOutdatedWatchers(watchers: IntentWatcher[], entity: Entity): Promise<IntentWatcher[]> {
        const diffs = await this.rediff(entity)
        for (let watcher of watchers) {
            if (IntentResolver.inTerminalState(watcher)) {
                continue
            }
            assert(watcher.spec_version < entity.metadata.spec_version, "Outdated watcher has spec version equal or higher than current")
            const intersection = IntentResolver.getIntersection(diffs, watcher.diffs, (diff, watcher_diff) => deepEqual(diff.diff_fields, watcher_diff.diff_fields))
            if (intersection.size === 0) {
                watcher.status = IntentfulStatus.Completed_Successfully
            } else if (intersection.size < watcher.diffs.length) {
                watcher.status = IntentfulStatus.Completed_Partially
            } else if (intersection.size >= watcher.diffs.length) {
                watcher.status = IntentfulStatus.Outdated
            }
            await this.intentWatcherDb.update_watcher(watcher.uuid, { status: watcher.status, last_status_changed: new Date() })
        }
        return watchers
    }

    private async processActiveWatcher(active: IntentWatcher, entity: Entity): Promise<IntentWatcher> {
        const diffs = await this.rediff(entity)
        const intersection = IntentResolver.getIntersection(diffs, active.diffs, (diff, watcher_diff) => deepEqual(diff.diff_fields, watcher_diff.diff_fields))
        if (intersection.size === 0) {
            active.status = IntentfulStatus.Completed_Successfully
            await this.intentWatcherDb.update_watcher(active.uuid, { status: active.status })
        } else if (intersection.size < active.diffs.length) {
            active.diffs = [...intersection]
            await this.intentWatcherDb.update_watcher(active.uuid, { diffs: active.diffs })
        }
        return active
    }

    private async processPendingWatchers(pending: IntentWatcher[], entity: Entity): Promise<IntentWatcher[]> {
        const diffs = await this.rediff(entity)
        for (let watcher of pending) {
            const intersection = IntentResolver.getIntersection(diffs, watcher.diffs, (diff, watcher_diff) => deepEqual(diff.diff_fields, watcher_diff.diff_fields))
            if (intersection.size === 0) {
                watcher.status = IntentfulStatus.Completed_Successfully
                await this.intentWatcherDb.update_watcher(watcher.uuid, { status: watcher.status })
            } else if (intersection.size < watcher.diffs.length) {
                watcher.status = IntentfulStatus.Active
                watcher.diffs = [...intersection]
                await this.intentWatcherDb.update_watcher(watcher.uuid, { diffs: watcher.diffs })
            }
        }
        return pending
    }

    private async onChange(entity: Entity) {
        try {
            const watchers = await this.intentWatcherDb.list_watchers({ entity_ref: { uuid: entity.metadata.uuid, kind: entity.metadata.kind } })
            const current_spec_version = entity.metadata.spec_version
            const latest_watcher = this.getLatestWatcher(watchers)
            if (latest_watcher && latest_watcher.spec_version === current_spec_version && latest_watcher.status === IntentfulStatus.Pending) {
                latest_watcher.status = IntentfulStatus.Active
                await this.intentWatcherDb.update_watcher(latest_watcher.uuid, { status: latest_watcher.status })
                await this.processActiveWatcher(latest_watcher, entity)
                const rest = watchers.filter(watcher => watcher.spec_version !== current_spec_version)
                await this.processOutdatedWatchers(rest, entity)
            } else if (latest_watcher && latest_watcher.spec_version === current_spec_version && latest_watcher.status === IntentfulStatus.Active) {
                await this.processActiveWatcher(latest_watcher, entity)
                const pending = watchers.filter(watcher => watcher.status === IntentfulStatus.Pending)
                await this.processPendingWatchers(pending, entity)
            }
        } catch (e) {
            this.logger.debug(`Couldn't process entity with uuid: ${entity.metadata.uuid}`)
        }
    }

    private getLatestWatcher(watchers: IntentWatcher[]): IntentWatcher | null {
        let latest_watcher: IntentWatcher | null = null
        for (let watcher of watchers) {
            if (!latest_watcher) {
                latest_watcher = watcher
            }
            if (watcher.spec_version > latest_watcher.spec_version) {
                latest_watcher = watcher
            }
        }
        return latest_watcher
    }

    private async onIntentfulHandlerFail(entity: EntryReference, error_msg?: string) {
        const watchers = await this.intentWatcherDb.list_watchers({ entity_ref: entity.entity_reference })
        const active_watcher = watchers.find(watcher => watcher.status === IntentfulStatus.Active)
        if (active_watcher) {
            active_watcher.times_failed += 1
            active_watcher.last_handler_error = error_msg
            await this.intentWatcherDb.update_watcher(active_watcher.uuid, { times_failed: active_watcher.times_failed, last_handler_error: active_watcher.last_handler_error })
        }
    }

    private async updateWatchersStatuses() {
        let entries = this.watchlist.entries();
        for (let key in entries) {
            if (!entries.hasOwnProperty(key)) {
                continue
            }
            const [entry_ref, diff, delay] = entries[key]
            const watchers = await this.intentWatcherDb.list_watchers({ entity_ref: entry_ref.entity_reference })
            if (watchers.length !== 0) {
                try {
                    const [metadata, spec] = await this.specDb.get_spec(entry_ref.entity_reference)
                    const [, status] = await this.statusDb.get_status({...entry_ref.provider_reference, ...entry_ref.entity_reference})
                    this.onChange({ metadata, spec, status })
                } catch (e) {

                }
            }
        }
    }

    public async run(delay: number, watcherExpirySeconds: number) {
        try {
            await this._run(delay, watcherExpirySeconds)
        } catch (e) {
            console.error(e)
            throw e
        }
    }

    protected async _run(delay: number, watcherExpirySeconds: number) {
        while (true) {
            await timeout(delay)
            this.clearTerminalStateWatchers(watcherExpirySeconds)
            this.updateWatchersStatuses()
        }
    }
}
