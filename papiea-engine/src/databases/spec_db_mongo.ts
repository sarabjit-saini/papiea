import { Spec_DB } from "./spec_db_interface";
import { Collection, Db } from "mongodb";
import { ConflictingEntityError, EntityNotFoundError } from "./utils/errors";
import { Entity_Reference, Metadata, Spec, Entity } from "papiea-core";
import { SortParams } from "../entity/entity_api_impl";
import { Logger, dotnotation } from "papiea-backend-utils";
import { IntentfulKindReference } from "./provider_db_mongo";
import { build_filter_query } from "./utils/filtering"

export class Spec_DB_Mongo implements Spec_DB {
    collection: Collection;
    logger: Logger;

    constructor(logger: Logger, db: Db) {
        this.collection = db.collection("entity");
        this.logger = logger;
    }

    async init(): Promise<void> {
        try {
            await this.collection.createIndex(
                { "metadata.uuid": 1, "metadata.provider_version": 1,
                    "metadata.kind": 1, "metadata.provider_prefix": 1 },
                { name: "provider_specific_entity_uuid", unique: true },
            );
        } catch (err) {
            throw err
        }
    }

    async update_spec(entity_metadata: Metadata, spec: Spec): Promise<[Metadata, Spec]> {
        let additional_fields: any = {};
        if (entity_metadata.extension !== undefined) {
            additional_fields = dotnotation({"metadata.extension": entity_metadata.extension});
        }
        additional_fields["metadata.created_at"] = new Date();
        const filter = {
            "metadata.uuid": entity_metadata.uuid,
            "metadata.kind": entity_metadata.kind,
            "metadata.spec_version": entity_metadata.spec_version,
            "metadata.provider_prefix": entity_metadata.provider_prefix,
            "metadata.provider_version": entity_metadata.provider_version
        };
        try {
            const result = await this.collection.updateOne(filter, {
                $inc: {
                    "metadata.spec_version": 1
                },
                $set: {
                    "spec": spec
                },
                $setOnInsert: additional_fields
            }, {
                    upsert: true
                });
            if (result.result.n !== 1) {
                throw new Error(`Amount of updated entries doesn't equal to 1: ${result.result.n}`)
            }
            return this.get_spec({ uuid: entity_metadata.uuid, kind: entity_metadata.kind });
        } catch (err) {
            if (err.code === 11000) {
                const entity_ref: Entity_Reference = { uuid: entity_metadata.uuid, kind: entity_metadata.kind };
                let res:any 
                try {
                  res = await this.get_spec(entity_ref);
                } catch (e) {
                    throw new Error(`Cannot create entity ${e}, ${err}`)
                }
                const [metadata, spec] = res
                throw new ConflictingEntityError("Spec with this version already exists", metadata, spec);
            } else {
                throw err;
            }
        }
    }

    async get_spec(entity_ref: Entity_Reference): Promise<[Metadata, Spec]> {
        const result: Entity | null = await this.collection.findOne({
            "metadata.uuid": entity_ref.uuid,
            "metadata.kind": entity_ref.kind,
            "metadata.deleted_at": null
        });
        if (result === null) {
            throw new EntityNotFoundError(entity_ref.kind, entity_ref.uuid)
        }
        return [result.metadata, result.spec];
    }

    async get_specs_by_ref(entity_refs: Entity_Reference[]): Promise<[Metadata, Spec][]> {
        const ids = entity_refs.map(ref => ref.uuid)
        const result = await this.collection.find({
            "metadata.uuid": {
                $in: ids
            }
        }).toArray();
        return result.map((x: any): [Metadata, Spec] => {
            if (x.spec !== null) {
                return [x.metadata, x.spec]
            } else {
                throw new Error("No valid entities found");
            }
        });
    }

    async list_specs(fields_map: any, exact_match: boolean, sortParams?: SortParams): Promise<([Metadata, Spec])[]> {
        const filter = build_filter_query(fields_map, exact_match)
        let result: any[];
        if (sortParams) {
            result = await this.collection.find(filter).sort(sortParams).toArray();
        } else {
            result = await this.collection.find(filter).toArray();
        }
        return result.map((x: any): [Metadata, Spec] => {
            if (x.spec !== null) {
                return [x.metadata, x.spec]
            } else {
                throw new Error("No valid entities found");
            }
        });
    }

    async list_specs_in(filter_list: any[], field_name: string = "metadata.uuid"): Promise<([Metadata, Spec])[]> {
        const result = await this.collection.find({ [field_name]: { $in: filter_list } }).sort({ "metadata.uuid": 1 }).toArray();
        return result.map((x: any): [Metadata, Spec] => {
            if (x.spec !== null) {
                return [x.metadata, x.spec]
            } else {
                throw new Error("No valid entities found");
            }
        });
    }

    async list_random_intentful_specs(size: number, kind_refs: IntentfulKindReference[], sortParams?: SortParams): Promise<([Metadata, Spec])[]> {
        const intentful_kind_names = kind_refs.map(kind => kind.kind_name)
        if (intentful_kind_names.length === 0) {
            return []
        }
        let result: any[];
        if (sortParams) {
            result = await this.collection.aggregate([
                { $match: { "metadata.kind": { $in: intentful_kind_names } } },
                { $sample: { size } }
            ]).sort(sortParams).toArray();
        } else {
            result = await this.collection.aggregate([
                { $match: { "metadata.kind": { $in: intentful_kind_names } } },
                { $sample: { size } }
            ]).toArray();
        }
        return result.map((x: any): [Metadata, Spec] => {
            if (x.spec !== null) {
                return [x.metadata, x.spec]
            } else {
                throw new Error("No valid entities found");
            }
        });
    }
}
