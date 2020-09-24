import axios from "axios"
import { Status_DB } from "../databases/status_db_interface";
import { Spec_DB } from "../databases/spec_db_interface";
import { Entity_API, OperationSuccess } from "./entity_api_interface";
import { Validator } from "../validator";
import { Authorizer } from "../auth/authz";
import { UserAuthInfo } from "../auth/authn";
import {
    Entity_Reference,
    Metadata,
    Procedural_Signature,
    Provider,
    Spec,
    Status,
    uuid4,
    Version,
    Action,
    Provider_Entity_Reference,
    Entity,
    IntentWatcher
} from "papiea-core";
import { ProcedureInvocationError } from "../errors/procedure_invocation_error";
import uuid = require("uuid");
import { PermissionDeniedError } from "../errors/permission_error";
import { Logger } from "papiea-backend-utils";
import { IntentfulContext } from "../intentful_core/intentful_context"
import { Provider_DB } from "../databases/provider_db_interface"
import { IntentWatcherMapper } from "../intentful_engine/intent_interface"
import { IntentWatcher_DB } from "../databases/intent_watcher_db_interface"
import { ConflictingEntityError } from "../databases/utils/errors"
import { Graveyard_DB } from "../databases/graveyard_db_interface"

export type SortParams = { [key: string]: number };

export class Entity_API_Impl implements Entity_API {
    private status_db: Status_DB;
    private spec_db: Spec_DB;
    private intent_watcher_db: IntentWatcher_DB
    private authorizer: Authorizer;
    private logger: Logger;
    private validator: Validator
    private readonly intentfulCtx: IntentfulContext
    private providerDb: Provider_DB
    private graveyardDb: Graveyard_DB

    constructor(logger: Logger, status_db: Status_DB, spec_db: Spec_DB, graveyardDb: Graveyard_DB, provider_db: Provider_DB, intent_watcher_db: IntentWatcher_DB, authorizer: Authorizer, validator: Validator, intentfulCtx: IntentfulContext) {
        this.status_db = status_db;
        this.spec_db = spec_db;
        this.graveyardDb = graveyardDb
        this.providerDb = provider_db;
        this.authorizer = authorizer;
        this.logger = logger;
        this.validator = validator;
        this.intentfulCtx = intentfulCtx
        this.intent_watcher_db = intent_watcher_db
    }

    private async get_provider(prefix: string, version: Version): Promise<Provider> {
        return this.providerDb.get_provider(prefix, version);
    }

    async get_intent_watcher(user: UserAuthInfo, id: string): Promise<Partial<IntentWatcher>> {
        const intent_watcher = await this.intent_watcher_db.get_watcher(id)
        const [metadata, _] = await this.spec_db.get_spec(intent_watcher.entity_ref)
        await this.authorizer.checkPermission(user, { "metadata": metadata }, Action.Update);
        return IntentWatcherMapper.toResponse(intent_watcher)
    }

    async filter_intent_watcher(user: UserAuthInfo, fields: any, sortParams?: SortParams): Promise<Partial<IntentWatcher>[]> {
        const intent_watchers = await this.intent_watcher_db.list_watchers(fields, sortParams)
        const entities = await this.spec_db.get_specs_by_ref(intent_watchers.map(watcher => watcher.entity_ref))
        const filteredRes = await this.authorizer.filter(user, entities, Action.Update, x => { return { "metadata": x[0] } });
        const filteredWatchers = IntentWatcherMapper.filter(intent_watchers, filteredRes)
        return IntentWatcherMapper.toResponses(filteredWatchers)
    }

    async save_entity(user: UserAuthInfo, prefix: string, kind_name: string, version: Version, spec_description: Spec, request_metadata: Metadata = {} as Metadata): Promise<[Metadata, Spec]> {
        const provider = await this.get_provider(prefix, version);
        const kind = this.providerDb.find_kind(provider, kind_name);
        this.validator.validate_metadata_extension(provider.extension_structure, request_metadata, provider.allowExtraProps);
        this.validator.validate_spec(spec_description, kind, provider.allowExtraProps);
        if (!request_metadata.uuid) {
            if (kind.uuid_validation_pattern === undefined) {
                request_metadata.uuid = uuid();
            } else {
                throw new Error("Uuid is not provided, but supposed to be since validation pattern is specified")
            }
        } else {
            const result = await this.get_existing_entities(provider, request_metadata.uuid, request_metadata.kind)
            if (result.length !== 0) {
                const [metadata, spec, status] = result
                throw new ConflictingEntityError("An entity with this uuid already exists", metadata, spec, status)
            }
        }
        this.validator.validate_uuid(kind, request_metadata.uuid)
        if (request_metadata.spec_version === undefined || request_metadata.spec_version === null) {
            let spec_version = await this.graveyardDb.get_highest_spec_version(
                {provider_prefix: prefix, kind: kind_name, provider_version: version, uuid: request_metadata.uuid})
            request_metadata.spec_version = spec_version
        }
        request_metadata.kind = kind.name;
        request_metadata.provider_prefix = prefix
        request_metadata.provider_version = version
        await this.authorizer.checkPermission(user, { "metadata": request_metadata }, Action.Create);
        const strategy = this.intentfulCtx.getIntentfulStrategy(kind, user)
        const [metadata, spec] = await strategy.create(request_metadata, spec_description)
        return [metadata, spec];
    }

    async get_entity_spec(user: UserAuthInfo, kind_name: string, entity_uuid: uuid4): Promise<[Metadata, Spec]> {
        const entity_ref: Entity_Reference = { kind: kind_name, uuid: entity_uuid };
        const [metadata, spec] = await this.spec_db.get_spec(entity_ref);
        await this.authorizer.checkPermission(user, { "metadata": metadata }, Action.Read);
        return [metadata, spec];
    }

    async get_entity_status(user: UserAuthInfo, prefix: string, version: Version, kind_name: string, entity_uuid: uuid4): Promise<[Metadata, Status]> {
        const entity_ref: Provider_Entity_Reference = { provider_prefix: prefix, provider_version: version,
            kind: kind_name, uuid: entity_uuid };
        const [metadata, status] = await this.status_db.get_status(entity_ref);
        await this.authorizer.checkPermission(user, { "metadata": metadata }, Action.Read);
        return [metadata, status];
    }

    async filter_entity_spec(user: UserAuthInfo, kind_name: string, fields: any, exact_match: boolean, sortParams?: SortParams): Promise<[Metadata, Spec][]> {
        fields.metadata.kind = kind_name;
        const res = await this.spec_db.list_specs(fields, exact_match, sortParams);
        const filteredRes = await this.authorizer.filter(user, res, Action.Read, x => { return { "metadata": x[0] } });
        return filteredRes;
    }

    async filter_entity_status(user: UserAuthInfo, kind_name: string, fields: any, exact_match: boolean, sortParams?: SortParams): Promise<[Metadata, Status][]> {
        fields.metadata.kind = kind_name;
        const res = await this.status_db.list_status(fields, exact_match, sortParams);
        const filteredRes = await this.authorizer.filter(user, res, Action.Read, x => { return { "metadata": x[0] } });
        return filteredRes;
    }

    async filter_deleted(user: UserAuthInfo, kind_name: string, fields: any, exact_match: boolean, sortParams?: SortParams): Promise<Entity[]> {
        fields.metadata.kind = kind_name;
        const res = await this.graveyardDb.list_entities(fields, exact_match, sortParams)
        const filteredRes = await this.authorizer.filter(user, res, Action.Read, x => { return { "metadata": x.metadata } });
        return filteredRes
    }

    async update_entity_spec(user: UserAuthInfo, uuid: uuid4, prefix: string, spec_version: number, extension: {[key: string]: any}, kind_name: string, version: Version, spec_description: Spec): Promise<IntentWatcher | null> {
        const provider = await this.get_provider(prefix, version);
        const kind = this.providerDb.find_kind(provider, kind_name);
        this.validator.validate_spec(spec_description, kind, provider.allowExtraProps);
        const entity_ref: Entity_Reference = { kind: kind_name, uuid: uuid };
        const metadata: Metadata = (await this.spec_db.get_spec(entity_ref))[0];
        await this.authorizer.checkPermission(user, { "metadata": metadata }, Action.Update);
        metadata.spec_version = spec_version;
        metadata.provider_prefix = prefix
        metadata.provider_version = version
        const strategy = this.intentfulCtx.getIntentfulStrategy(kind, user)
        const watcher = await strategy.update(metadata, spec_description)
        return watcher;
    }

    async delete_entity(user: UserAuthInfo, prefix: string, version: Version, kind_name: string, entity_uuid: uuid4): Promise<void> {
        const provider = await this.get_provider(prefix, version);
        const kind = this.providerDb.find_kind(provider, kind_name);
        const entity_ref: Provider_Entity_Reference = { kind: kind_name, uuid: entity_uuid, provider_prefix: prefix, provider_version: version };
        const [metadata, spec] = await this.spec_db.get_spec(entity_ref);
        const [_, status] = await this.status_db.get_status(entity_ref);
        await this.authorizer.checkPermission(user, { "metadata": metadata }, Action.Delete);
        const strategy = this.intentfulCtx.getIntentfulStrategy(kind, user)
        await strategy.delete({ metadata, spec, status })
    }

    async call_procedure(user: UserAuthInfo, prefix: string, kind_name: string, version: Version, entity_uuid: uuid4, procedure_name: string, input: any): Promise<any> {
        const provider = await this.get_provider(prefix, version);
        const kind = this.providerDb.find_kind(provider, kind_name);
        const entity_spec: [Metadata, Spec] = await this.get_entity_spec(user, kind_name, entity_uuid);
        const entity_status: [Metadata, Status] = await this.get_entity_status(
            user, prefix, version, kind_name, entity_uuid);
        const procedure: Procedural_Signature | undefined = kind.entity_procedures[procedure_name];
        if (procedure === undefined) {
            throw new Error(`Procedure ${procedure_name} not found for kind ${kind.name}`);
        }
        const schemas: any = {};
        Object.assign(schemas, procedure.argument);
        Object.assign(schemas, procedure.result);
        try {
            this.validator.validate(input, Object.values(procedure.argument)[0], schemas,
                provider.allowExtraProps, Object.keys(procedure.argument)[0], procedure_name);
        } catch (err) {
            throw ProcedureInvocationError.fromError(err, 400)
        }
        try {
            const { data } = await axios.post(procedure.procedure_callback,
                {
                    metadata: entity_spec[0],
                    spec: entity_spec[1],
                    status: entity_status[1],
                    input: input
                }, {
                    headers: user
                });
            this.validator.validate(data, Object.values(procedure.result)[0], schemas,
                provider.allowExtraProps, Object.keys(procedure.argument)[0], procedure_name);
            return data;
        } catch (err) {
            throw ProcedureInvocationError.fromError(err)
        }
    }

    async call_provider_procedure(user: UserAuthInfo, prefix: string, version: Version, procedure_name: string, input: any): Promise<any> {
        const provider = await this.get_provider(prefix, version);
        if (provider.procedures === undefined) {
            throw new Error(`Procedure ${procedure_name} not found for provider ${prefix}`);
        }
        const procedure: Procedural_Signature | undefined = provider.procedures[procedure_name];
        if (procedure === undefined) {
            throw new Error(`Procedure ${procedure_name} not found for provider ${prefix}`);
        }
        const schemas: any = {};
        Object.assign(schemas, procedure.argument);
        Object.assign(schemas, procedure.result);
        try {
            this.validator.validate(input, Object.values(procedure.argument)[0], schemas,
                provider.allowExtraProps, Object.keys(procedure.argument)[0], procedure_name);
        } catch (err) {
            throw ProcedureInvocationError.fromError(err, 400)
        }
        try {
            const { data } = await axios.post(procedure.procedure_callback,
                {
                    input: input
                }, {
                    headers: user
                });
            this.validator.validate(data, Object.values(procedure.result)[0], schemas,
                provider.allowExtraProps, Object.keys(procedure.argument)[0], procedure_name);
            return data;
        } catch (err) {
            throw ProcedureInvocationError.fromError(err)
        }
    }

    async call_kind_procedure(user: UserAuthInfo, prefix: string, kind_name: string, version: Version, procedure_name: string, input: any): Promise<any> {
        const provider = await this.get_provider(prefix, version);
        const kind = this.providerDb.find_kind(provider, kind_name);
        const procedure: Procedural_Signature | undefined = kind.kind_procedures[procedure_name];
        if (procedure === undefined) {
            throw new Error(`Procedure ${procedure_name} not found for kind ${kind.name}`);
        }
        const schemas: any = {};
        Object.assign(schemas, procedure.argument);
        Object.assign(schemas, procedure.result);
        try {
            this.validator.validate(input, Object.values(procedure.argument)[0], schemas,
                provider.allowExtraProps, Object.keys(procedure.argument)[0], procedure_name);
        } catch (err) {
            throw ProcedureInvocationError.fromError(err, 400)
        }
        try {
            const { data } = await axios.post(procedure.procedure_callback,
                {
                    input: input
                }, {
                    headers: user
                });
            this.validator.validate(data, Object.values(procedure.result)[0], schemas,
                provider.allowExtraProps, Object.keys(procedure.argument)[0], procedure_name);
            return data;
        } catch (err) {
            throw ProcedureInvocationError.fromError(err)
        }
    }

    async check_permission(user: UserAuthInfo, prefix: string, version: Version, entityAction: [Action, Entity_Reference][]): Promise<OperationSuccess> {
        if (entityAction.length === 1) {
            return await this.check_single_permission(user, prefix, version, entityAction[0])
        } else {
            return await this.check_multiple_permissions(user, prefix, version, entityAction)
        }
    }

    async check_single_permission(user: UserAuthInfo, prefix: string, version: Version, entityAction: [Action, Entity_Reference]): Promise<OperationSuccess> {
        const [action, entityRef] = entityAction;
        if (action === Action.Create) {
            const has_perm = await this.has_permission(user, entityRef as Metadata, action)
            if (has_perm) {
                return {"success": "Ok"}
            } else {
                throw new PermissionDeniedError()
            }
        } else {
            const [metadata, _] = await this.spec_db.get_spec(entityRef);
            const has_perm = await this.has_permission(user, metadata, action)
            if (has_perm) {
                return {"success": "Ok"}
            } else {
                throw new PermissionDeniedError()
            }
        }
    }

    async check_multiple_permissions(user: UserAuthInfo, prefix: string, version: Version, entityAction: [Action, Entity_Reference][]): Promise<OperationSuccess> {
        const checkPromises: Promise<boolean>[] = [];
        for (let [action, entityRef] of entityAction) {
            if (action === Action.Create) {
                checkPromises.push(this.has_permission(user, entityRef as Metadata, action));
            } else {
                const [metadata, _] = await this.spec_db.get_spec(entityRef);
                checkPromises.push(this.has_permission(user, metadata, action));
            }
        }
        const has_perm = (await Promise.all(checkPromises)).every((val, index, arr) => val)
        if (has_perm) {
            return { "success": "Ok" }
        } else {
            throw new PermissionDeniedError()
        }
    }

    async has_permission(user: UserAuthInfo, metadata: Metadata, action: Action) {
        try {
            await this.authorizer.checkPermission(user, { "metadata": metadata }, action);
            return true;
        } catch (e) {
            return false;
        }
    }

    private async get_existing_entities(provider: Provider, uuid: string, kind_name: string): Promise<[Metadata, Spec, Status] | []> {
        try {
            const result_spec = await this.spec_db.list_specs({ metadata: { uuid: uuid, kind: kind_name, provider_version: provider.version, provider_prefix: provider.prefix, deleted_at: null } }, false)
            const result_status = await this.status_db.list_status({ metadata: { uuid: uuid, kind: kind_name, provider_version: provider.version, provider_prefix: provider.prefix, deleted_at: null } }, false)
            if (result_spec.length !== 0 || result_status.length !== 0) {
                return [result_spec[0][0], result_spec[0][1], result_status[0][1]]
            } else {
                return []
            }
        } catch (e) {
            // Hiding details of the error for security reasons
            // since it is not supposed to occur under normal circumstances
            throw new Error("uuid is not valid")
        }
    }
}
