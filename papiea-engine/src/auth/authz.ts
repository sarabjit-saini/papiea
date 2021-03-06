import { UserAuthInfo } from "./authn";
import { Provider_API } from "../provider/provider_api_interface";
import { Provider, Action } from "papiea-core";
import { PermissionDeniedError, UnauthorizedError } from "../errors/permission_error";
import { Logger } from 'papiea-backend-utils'

function mapAsync<T, U>(array: T[], callbackfn: (value: T, index: number, array: T[]) => Promise<U>): Promise<U[]> {
    return Promise.all(array.map(callbackfn));
}

async function filterAsync<T>(array: T[], callbackfn: (value: T, index: number, array: T[]) => Promise<boolean>): Promise<T[]> {
    const filterMap = await mapAsync(array, callbackfn);
    return array.filter((value, index) => filterMap[index]);
}

export abstract class Authorizer {
    constructor() {
    }

    abstract checkPermission(user: UserAuthInfo, object: any, action: Action): Promise<void>;

    async filter(user: UserAuthInfo, objectList: any[], action: Action, transformfn?: (object: any) => any): Promise<any[]> {
        return filterAsync(objectList, async (object) => {
            try {
                if (transformfn) {
                    await this.checkPermission(user, transformfn(object), action);
                } else {
                    await this.checkPermission(user, object, action);
                }
                return true;
            } catch (e) {
                return false;
            }
        });
    }
}

export class NoAuthAuthorizer extends Authorizer {
    async checkPermission(user: UserAuthInfo, object: any, action: Action): Promise<void> {
    }
}

export interface ProviderAuthorizerFactory {
    createAuthorizer(provider: Provider): Promise<Authorizer>;
}

export class PerProviderAuthorizer extends Authorizer {
    private providerApi: Provider_API;
    private providerToAuthorizer: { [key: string]: Authorizer | null; };
    private kindToProviderPrefix: { [key: string]: string; };
    private providerAuthorizerFactory: ProviderAuthorizerFactory;
    private logger: Logger;

    constructor(logger: Logger, providerApi: Provider_API, providerAuthorizerFactory: ProviderAuthorizerFactory) {
        super();
        this.providerApi = providerApi;
        providerApi.on_auth_change((provider: Provider) => {
            delete this.providerToAuthorizer[provider.prefix];
        });
        this.providerToAuthorizer = {};
        this.kindToProviderPrefix = {};
        this.providerAuthorizerFactory = providerAuthorizerFactory;
        this.logger = logger;
    }

    private async getProviderPrefixByKindName(user: UserAuthInfo, kind_name: string): Promise<string> {
        if (kind_name in this.kindToProviderPrefix) {
            return this.kindToProviderPrefix[kind_name];
        }
        const provider: Provider = await this.providerApi.get_latest_provider_by_kind(user, kind_name);
        if (!provider) {
            throw new PermissionDeniedError();
        }
        this.kindToProviderPrefix[kind_name] = provider.prefix;
        return provider.prefix;
    }

    private async getProviderPrefixByObject(user: UserAuthInfo, object: any): Promise<string> {
        if (object.metadata && object.metadata.kind) {
            return this.getProviderPrefixByKindName(user, object.metadata.kind);
        } else if (object.kind) {
            return this.getProviderPrefixByKindName(user, object.kind.name);
        } else if (object.provider) {
            return object.provider.prefix;
        }
        throw new PermissionDeniedError();
    }

    private async getAuthorizerByObject(user: UserAuthInfo, object: any): Promise<Authorizer | null> {
        const providerPrefix = await this.getProviderPrefixByObject(user, object);
        if (providerPrefix in this.providerToAuthorizer) {
            return this.providerToAuthorizer[providerPrefix];
        }
        const provider: Provider = await this.providerApi.get_latest_provider(user, providerPrefix);
        if (!provider.authModel || !provider.policy) {
            this.providerToAuthorizer[providerPrefix] = null;
            return null;
        }
        const authorizer = await this.providerAuthorizerFactory.createAuthorizer(provider);
        this.providerToAuthorizer[providerPrefix] = authorizer;
        return authorizer;
    }

    async checkPermission(user: UserAuthInfo, object: any, action: Action): Promise<void> {
        const authorizer: Authorizer | null = await this.getAuthorizerByObject(user, object);
        if (authorizer === null) {
            return;
        }
        if (!user) {
            throw new UnauthorizedError();
        }
        if (user.is_admin) {
            return;
        }
        if (user.is_provider_admin) {
            const providerPrefix = await this.getProviderPrefixByObject(user, object);
            // For provider-admin provider_prefix must be set
            if (user.provider_prefix === providerPrefix) {
                return;
            } else {
                throw new PermissionDeniedError();
            }
        }
        return authorizer.checkPermission(user, object, action);
    }
}

export class AdminAuthorizer extends Authorizer {
    async checkPermission(user: UserAuthInfo, object: any, action: Action): Promise<void> {
        if (!user) {
            throw new UnauthorizedError();
        }
        if (user.is_admin) {
            return;
        }
        if (action === Action.CreateS2SKey) {
            // object.user_info contains UserInfo which will be used when s2s key is passed
            // check who can talk on behalf of whom
            if (object.owner !== user.owner || object.user_info.is_admin) {
                throw new PermissionDeniedError();
            }
            if (user.provider_prefix !== undefined
                && object.provider_prefix !== user.provider_prefix) {
                throw new PermissionDeniedError();
            }
            if (user.is_provider_admin) {
                return;
            }
            if (object.user_info.is_provider_admin
                || object.user_info.owner !== user.owner) {
                throw new PermissionDeniedError();
            }
            return;
        }
        if (action === Action.ReadS2SKey || action === Action.InactivateS2SKey) {
            if (object.owner !== user.owner
                || (user.provider_prefix !== undefined && object.provider_prefix !== user.provider_prefix)) {
                throw new PermissionDeniedError();
            } else {
                return;
            }
        }
        if (user.is_provider_admin && object.prefix === user.provider_prefix) {
            return;
        }
        throw new PermissionDeniedError();
    }
}
