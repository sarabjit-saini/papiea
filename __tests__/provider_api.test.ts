import "jest"
import axios from "axios"
import { Provider } from "../src/papiea";
import { getProviderWithSpecOnlyEnitityKindNoOperations } from "./test_data_factory";

declare var process: {
    env: {
        SERVER_PORT: string
    }
};
const serverPort = parseInt(process.env.SERVER_PORT || '3000');

const providerApi = axios.create({
    baseURL: `http://127.0.0.1:${ serverPort }/provider/`,
    timeout: 1000,
    headers: { 'Content-Type': 'application/json' }
});

const entityApi = axios.create({
    baseURL: `http://127.0.0.1:${ serverPort }/entity`,
    timeout: 1000,
    headers: { 'Content-Type': 'application/json' }
});

describe("Provider API tests", () => {
    const providerPrefix = "test_provider";
    const providerVersion = "0.1.0";
    test("Non-existent route", done => {
        providerApi.delete(`/abc`).then(() => done.fail()).catch(() => done());
    });
    test("Register provider", done => {
        const provider: Provider = { prefix: providerPrefix, version: providerVersion, kinds: [] };
        providerApi.post('/', provider).then(() => done()).catch(done.fail);
    });
    test("Register malformed provider", done => {
        providerApi.post('/', {}).then(() => done.fail()).catch(() => done());
    });
    // TODO(adolgarev): there is no API to list providers
    test("Unregister provider", done => {
        providerApi.delete(`/${ providerPrefix }/${ providerVersion }`).then(() => done()).catch(done.fail);
    });
    test("Unregister non-existend provider", done => {
        providerApi.delete(`/${ providerPrefix }/${ providerVersion }`).then(() => done.fail()).catch(() => done());
    });
    test("Unregister never existed provider", done => {
        providerApi.delete(`/123/123`).then(() => done.fail()).catch(() => done());
    });
    test("Update status", async done => {
        const provider: Provider = getProviderWithSpecOnlyEnitityKindNoOperations();
        await providerApi.post('/', provider);
        const kind_name = provider.kinds[0].name;
        const { data: { metadata, spec } } = await entityApi.post(`/${ provider.prefix }/${ kind_name }`, {
            spec: {
                x: 10,
                y: 11
            }
        });

        providerApi.post('/update_status', {
            context: "some context",
            entity_ref: {
                uuid: metadata.uuid,
                kind: kind_name
            },
            status: { x: 10, y: 20 }
        }).then(() => done()).catch(done.fail);
    });

    test("Update status with malformed status should fail validation", async done => {
        const provider: Provider = getProviderWithSpecOnlyEnitityKindNoOperations();
        await providerApi.post('/', provider);
        const kind_name = provider.kinds[0].name;
        const { data: { metadata, spec } } = await entityApi.post(`/${ provider.prefix }/${ kind_name }`, {
            spec: {
                x: 10,
                y: 11
            }
        });

        try {
            await providerApi.post('/update_status', {
                context: "some context",
                entity_ref: {
                    uuid: metadata.uuid,
                    kind: kind_name
                },
                status: { x: 11, y: "Totally not a number" }
            });
        } catch (err) {
            done();
        }
    });
    // TODO(adolgarev): there is no API at the moment to list statuses
});