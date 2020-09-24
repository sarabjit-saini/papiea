import { Spec, uuid4, Metadata, Status } from "papiea-core";

export class ConflictingEntityError extends Error {

    existing_metadata: Metadata;
    existing_spec: Spec;
    existing_status?: Status

    constructor(msg: string, metadata: Metadata, spec: Spec, status?: Status) {
        super(msg);
        this.existing_metadata = metadata;
        this.existing_spec = spec;
        this.existing_status = status
    }
}

export class GraveyardConflictingEntityError extends ConflictingEntityError {
    private static MESSAGE = "Deleted entity with this uuid and spec version exists"

    highest_spec_version: number

    constructor(metadata: Metadata, spec: Spec, highest_spec_version: number, status?: Status) {
        super(GraveyardConflictingEntityError.MESSAGE, metadata, spec, status);
        this.highest_spec_version = highest_spec_version
    }
}

export class EntityNotFoundError extends Error {

    uuid: uuid4;
    kind: string;

    constructor(kind: string, uuid: uuid4) {
        super();
        this.kind = kind;
        this.uuid = uuid;
    }
}
