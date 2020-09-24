import { Spec_DB } from "../databases/spec_db_interface"
import { Status_DB } from "../databases/status_db_interface"
import { IntentfulStrategy } from "./intentful_strategies/intentful_strategy_interface"
import { BasicIntentfulStrategy } from "./intentful_strategies/basic_intentful_strategy"
import { IntentfulBehaviour, Kind, Differ, DiffSelectionStrategy } from "papiea-core"
import { SpecOnlyIntentfulStrategy } from "./intentful_strategies/spec_only_intentful_strategy"
import { UserAuthInfo } from "../auth/authn"
import { DifferIntentfulStrategy } from "./intentful_strategies/differ_intentful_strategy"
import { IntentWatcher_DB } from "../databases/intent_watcher_db_interface"
import { BasicDiffSelectionStrategy } from "./diff_selection_strategies/basic_diff_selection_strategy";
import { DiffSelectionStrategyInterface } from "./diff_selection_strategies/diff_selection_strategy_interface";
import { RandomDiffSelectionStrategy } from "./diff_selection_strategies/random_diff_selection_strategy";
import { Watchlist_DB } from "../databases/watchlist_db_interface";
import {
    BasicUpdateStrategy, DifferUpdateStrategy,
    SpecOnlyUpdateStrategy,
    StatusUpdateStrategy
} from "./intentful_strategies/status_update_strategy";
import { Graveyard_DB } from "../databases/graveyard_db_interface"

export type BehaviourStrategyMap = Map<IntentfulBehaviour, IntentfulStrategy>
export type DiffSelectionStrategyMap = Map<DiffSelectionStrategy, DiffSelectionStrategyInterface>
export type StatusUpdateStrategyMap = Map<IntentfulBehaviour, StatusUpdateStrategy>

export class IntentfulContext {
    private readonly behaviourStrategyMap: BehaviourStrategyMap
    private readonly diffSelectionStrategyMap: DiffSelectionStrategyMap
    private readonly statusUpdateStrategyMap: StatusUpdateStrategyMap

    constructor(specDb: Spec_DB, statusDb: Status_DB, graveyardDb: Graveyard_DB, differ: Differ, intentWatcherDb: IntentWatcher_DB, watchlistDb: Watchlist_DB) {
        this.behaviourStrategyMap = new Map()
        this.behaviourStrategyMap.set(IntentfulBehaviour.Basic, new BasicIntentfulStrategy(specDb, statusDb, graveyardDb))
        this.behaviourStrategyMap.set(IntentfulBehaviour.SpecOnly, new SpecOnlyIntentfulStrategy(specDb, statusDb, graveyardDb))
        this.behaviourStrategyMap.set(IntentfulBehaviour.Differ, new DifferIntentfulStrategy(specDb, statusDb, graveyardDb, differ, intentWatcherDb, watchlistDb))

        this.diffSelectionStrategyMap = new Map()
        this.diffSelectionStrategyMap.set(DiffSelectionStrategy.Basic, new BasicDiffSelectionStrategy())
        this.diffSelectionStrategyMap.set(DiffSelectionStrategy.Random, new RandomDiffSelectionStrategy())

        this.statusUpdateStrategyMap = new Map()
        this.statusUpdateStrategyMap.set(IntentfulBehaviour.Basic, new BasicUpdateStrategy(statusDb))
        this.statusUpdateStrategyMap.set(IntentfulBehaviour.SpecOnly, new SpecOnlyUpdateStrategy(statusDb))
        this.statusUpdateStrategyMap.set(IntentfulBehaviour.Differ, new DifferUpdateStrategy(statusDb, specDb, differ, watchlistDb))
    }

    getIntentfulStrategy(kind: Kind, user: UserAuthInfo): IntentfulStrategy {
        const strategy = this.behaviourStrategyMap.get(kind.intentful_behaviour)
        if (strategy === undefined) {
            throw new Error(`Strategy associated with behaviour: ${kind.intentful_behaviour} not found`)
        }
        strategy.setKind(kind)
        strategy.setUser(user)
        return strategy
    }

    getDiffSelectionStrategy(kind: Kind): DiffSelectionStrategyInterface {
        const strategy = this.diffSelectionStrategyMap.get(kind.diff_selection_strategy || DiffSelectionStrategy.Random)
        return strategy!
    }

    getStatusUpdateStrategy(kind: Kind, user: UserAuthInfo): StatusUpdateStrategy {
        const strategy = this.statusUpdateStrategyMap.get(kind.kind_structure[kind.name]['x-papiea-entity'])
        if (strategy === undefined) {
            throw new Error(`Strategy associated with behaviour: ${kind.intentful_behaviour} not found`)
        }
        strategy.setKind(kind)
        strategy.setUser(user)
        return strategy
    }
}
