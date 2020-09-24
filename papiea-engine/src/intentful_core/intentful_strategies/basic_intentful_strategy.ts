import { IntentfulStrategy } from "./intentful_strategy_interface"
import { Spec_DB } from "../../databases/spec_db_interface"
import { Status_DB } from "../../databases/status_db_interface"
import { Metadata, Spec, Entity, IntentWatcher } from "papiea-core"
import { Graveyard_DB } from "../../databases/graveyard_db_interface"


export class BasicIntentfulStrategy extends IntentfulStrategy {
    constructor(specDb: Spec_DB, statusDb: Status_DB, graveyardDb: Graveyard_DB) {
        super(specDb, statusDb, graveyardDb)
    }

    // Update spec and status with spec changes received
    async update(metadata: Metadata, spec: Spec): Promise<IntentWatcher | null> {
        await this.update_entity(metadata, spec)
        return null
    }

    // Create status with spec
    async create(metadata: Metadata, spec: Spec): Promise<[Metadata, Spec]> {
        return this.create_entity(metadata, spec)
    }

    // Simply delete from DB both spec and status
    async delete(entity: Entity): Promise<void> {
        return this.delete_entity(entity)
    }
}
