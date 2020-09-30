import { logLevelFromString, LoggerFactory } from "papiea-backend-utils"
import { MongoConnection } from "./databases/mongo"
import { Watchlist } from "./intentful_engine/watchlist"
import { DiffResolver } from "./intentful_engine/diff_resolver"
import { BasicDiffer } from "./intentful_core/differ_impl";
import { IntentfulContext } from "./intentful_core/intentful_context";
import { IntentResolver } from "./intentful_engine/intent_resolver";
import { IntentfulListenerMongo } from "./intentful_engine/intentful_listener_mongo_simple";
import { getEntropyFn } from "./utils/utils"

declare var process: {
    env: {
        SERVER_PORT: string,
        MONGO_DB: string,
        MONGO_URL: string,
        PAPIEA_PUBLIC_URL: string,
        DEBUG_LEVEL: string,
        PAPIEA_ADMIN_S2S_KEY: string,
        LOGGING_LEVEL: string
        PAPIEA_DEBUG: string,
        DELETED_WATCHER_PERSIST_SECONDS: number,
        RANDOM_ENTITY_BATCH_SIZE: number,
    },
    title: string;
};

const mongoUrl = process.env.MONGO_URL || 'mongodb://mongo:27017';
const mongoDb = process.env.MONGO_DB || 'papiea';
const loggingLevel = logLevelFromString(process.env.LOGGING_LEVEL) ?? 'debug';
const batchSize = process.env.RANDOM_ENTITY_BATCH_SIZE ?? 5
const deletedWatcherPersists = process.env.DELETED_WATCHER_PERSIST_SECONDS ?? 100
const papieaDebug = process.env.PAPIEA_DEBUG === "true"

async function setUpDiffResolver() {
    const logger = LoggerFactory.makeLogger({level: loggingLevel});
    const mongoConnection: MongoConnection = new MongoConnection(mongoUrl, mongoDb);
    await mongoConnection.connect();

    const specDb = await mongoConnection.get_spec_db(logger);
    const statusDb = await mongoConnection.get_status_db(logger);
    const providerDb = await mongoConnection.get_provider_db(logger);
    const intentWatcherDB = await mongoConnection.get_intent_watcher_db(logger)
    const watchlistDb = await mongoConnection.get_watchlist_db(logger)
    const graveyardDb = await mongoConnection.get_graveyard_db(logger)

    const differ = new BasicDiffer()
    const intentfulContext = new IntentfulContext(specDb, statusDb, graveyardDb, differ, intentWatcherDB, watchlistDb)
    const watchlist: Watchlist = new Watchlist()

    const intentfulListenerMongo = new IntentfulListenerMongo(statusDb, specDb, watchlist)
    intentfulListenerMongo.run(250)
    const entropyFunction = getEntropyFn(papieaDebug)

    const diffResolver = new DiffResolver(watchlist, watchlistDb, specDb, statusDb, providerDb, differ, intentfulContext, logger, batchSize, entropyFunction)

    const intentResolver = new IntentResolver(specDb, statusDb, intentWatcherDB, providerDb, intentfulListenerMongo, differ, diffResolver, watchlist, logger)

    console.log("Running diff resolver")

    intentResolver.run(3000, deletedWatcherPersists)
    await diffResolver.run(1500)
}

setUpDiffResolver().then(()=>console.debug("Exiting diff resolver")).catch(console.error)
