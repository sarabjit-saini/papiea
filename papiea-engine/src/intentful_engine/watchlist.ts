import { Diff, Entity_Reference, Version, Metadata } from "papiea-core"

// I don't like the provider being necessary here too much, maybe rethink this
export interface EntryReference {
    provider_reference: {
        provider_prefix: string,
        provider_version: Version
    },
    entity_reference: Entity_Reference
}
const stringifyEntryRef = (r: EntryReference) => [
    r.provider_reference.provider_prefix,
    r.provider_reference.provider_version,
    r.entity_reference.kind,
    r.entity_reference.uuid,
].join('/')

export interface Delay {
    delaySetTime: Date
    delay_seconds: number
}

export function create_entry(metadata: Metadata): EntryReference {
    return {
        provider_reference: {
            provider_prefix: metadata.provider_prefix,
            provider_version: metadata.provider_version
        },
        entity_reference: {
            uuid: metadata.uuid,
            kind: metadata.kind
        }
    }
}

export type SerializedWatchlist = {[key: string]: Watch}
export type WatchlistEntries = Watch[]
type Watch = [EntryReference, Diff | undefined, Delay | undefined]

export class Watchlist {
    private _entries: SerializedWatchlist

    constructor(watchlist?: SerializedWatchlist) {
        this._entries = watchlist ?? {}
    }

    get(ref: EntryReference): Watch | undefined {
        return this._entries[stringifyEntryRef(ref)]
    }

    set(value: Watch): this {
        this._entries[stringifyEntryRef(value[0])] = value
        return this
    }

    delete(ref: EntryReference): boolean {
        let exists: boolean
        if (this._entries[stringifyEntryRef(ref)]) {
            exists = true
        } else {
            exists = false
        }
        delete this._entries[stringifyEntryRef(ref)]
        return exists
    }

    update(watchlist: Watchlist) {
        this._entries = watchlist._entries
    }

    serialize(): SerializedWatchlist {
        return this._entries
    }

    entries(): SerializedWatchlist {
        return this._entries
    }

    has(ref: EntryReference): boolean {
        const item = this._entries[stringifyEntryRef(ref)]
        return item !== undefined;
    }
}
