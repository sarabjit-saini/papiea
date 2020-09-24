import { Collection, Db } from "mongodb"
import { SortParams } from "../entity/entity_api_impl"
import { Logger } from 'papiea-backend-utils'
import { IntentWatcher_DB } from "./intent_watcher_db_interface"
import { IntentWatcher } from "papiea-core"

export class IntentWatcher_DB_Mongo implements IntentWatcher_DB {
    collection: Collection;
    logger: Logger;

    constructor(logger: Logger, db: Db) {
        this.collection = db.collection("watcher");
        this.logger = logger;
    }

    async init(): Promise<void> {
        try {
            await this.collection.createIndex(
                { "uuid": 1 },
                { unique: true },
            )
        } catch (err) {
            throw err
        }
    }

    async save_watcher(watcher: IntentWatcher): Promise<void> {
        watcher.created_at = new Date()
        await this.collection.insertOne(watcher);
    }

    async get_watcher(uuid: string): Promise<IntentWatcher> {
        const result: IntentWatcher | null = await this.collection.findOne({
            "uuid": uuid,
        });
        if (result === null) {
            throw new Error("key not found");
        }
        return result;
    }

    async update_watcher(uuid: string, delta: Partial<IntentWatcher>): Promise<void> {
        const result = await this.collection.updateOne({
            uuid
        }, {
            $set: delta
        })
        if (result.result.n === undefined || result.result.ok !== 1) {
            throw new Error("Failed update intent watcher");
        }
        if (result.result.n !== 1 && result.result.n !== 0) {
            throw new Error(`Amount of intent watchers updated must be 0 or 1, found: ${result.result.n}`);
        }
    }


    async list_watchers(fields_map: any, sortParams?: SortParams): Promise<IntentWatcher[]> {
        const filter: any = Object.assign({}, fields_map);
        if (sortParams) {
            return await this.collection.find(filter).sort(sortParams).toArray();
        } else {
            return await this.collection.find(filter).toArray();
        }
    }

    async delete_watcher(uuid: string): Promise<void> {
        const result = await this.collection.deleteOne({
            uuid
        })
        if (result.result.n === undefined || result.result.ok !== 1) {
            throw new Error("Failed to delete a intent watcher");
        }
        if (result.result.n !== 1 && result.result.n !== 0) {
            throw new Error(`Amount of deleted intent watchers must be 0 or 1, found: ${result.result.n}`);
        }
        return;
    }
}
