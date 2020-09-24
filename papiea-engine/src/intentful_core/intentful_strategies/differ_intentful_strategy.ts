import { IntentfulStrategy } from "./intentful_strategy_interface"
import { Spec_DB } from "../../databases/spec_db_interface"
import { Status_DB } from "../../databases/status_db_interface"
import { Differ, Metadata, Spec, IntentWatcher } from "papiea-core"
import { IntentWatcher_DB } from "../../databases/intent_watcher_db_interface"
import { IntentfulStatus } from "papiea-core"
import { Watchlist_DB } from "../../databases/watchlist_db_interface";
import uuid = require("uuid")
import { create_entry } from "../../intentful_engine/watchlist";
import { Graveyard_DB } from "../../databases/graveyard_db_interface"

export class DifferIntentfulStrategy extends IntentfulStrategy {
    protected differ: Differ
    protected intentWatcherDb: IntentWatcher_DB
    protected watchlistDb: Watchlist_DB;

    constructor(specDb: Spec_DB, statusDb: Status_DB, graveyardDb: Graveyard_DB, differ: Differ, intentWatcherDb: IntentWatcher_DB, watchlistDb: Watchlist_DB) {
        super(specDb, statusDb, graveyardDb)
        this.differ = differ
        this.intentWatcherDb = intentWatcherDb
        this.watchlistDb = watchlistDb
    }

    async create_entity(metadata: Metadata, spec: Spec): Promise<[Metadata, Spec]> {
        const [updatedMetadata, updatedSpec] = await this.specDb.update_spec(metadata, spec);
        return [updatedMetadata, updatedSpec]
    }

    async update_entity(metadata: Metadata, spec: Spec): Promise<[Metadata, Spec]> {
        const [updatedMetadata, updatedSpec] = await this.specDb.update_spec(metadata, spec);
        return [updatedMetadata, updatedSpec]
    }

    async update(metadata: Metadata, spec: Spec): Promise<IntentWatcher | null> {
        const [_, status] = await this.statusDb.get_status(metadata)
        let watcher_spec_version = metadata.spec_version + 1
        const watcher: IntentWatcher = {
            uuid: uuid(),
            entity_ref: {
                uuid: metadata.uuid,
                kind: metadata.kind
            },
            diffs: [],
            spec_version: watcher_spec_version,
            user: this.user,
            status: IntentfulStatus.Pending,
            times_failed: 0
        }
        for (let diff of this.differ.diffs(this.kind!, spec, status)) {
            watcher.diffs.push(diff)
        }
        await this.intentWatcherDb.save_watcher(watcher)
        const watchlist = await this.watchlistDb.get_watchlist()
        const ent = create_entry(metadata)
        if (!watchlist.has(ent)) {
            watchlist.set([ent, undefined, undefined])
            await this.watchlistDb.update_watchlist(watchlist)
        }
        try {
            await this.update_entity(metadata, spec)
        } catch (e) {
            watcher.times_failed++
            watcher.last_handler_error = e.message
            watcher.status = IntentfulStatus.Failed
            await this.intentWatcherDb.update_watcher(watcher.uuid, { ...watcher })
            throw e
        }
        return watcher
    }

    async create(metadata: Metadata, spec: Spec): Promise<[Metadata, Spec]> {
        const [created_metadata, created_spec] = await super.create(metadata, spec)
        const watchlist = await this.watchlistDb.get_watchlist()
        const ent = create_entry(created_metadata)
        if (!watchlist.has(ent)) {
            watchlist.set([ent, undefined, undefined])
            await this.watchlistDb.update_watchlist(watchlist)
        }
        return [created_metadata, created_spec]
    }
}
