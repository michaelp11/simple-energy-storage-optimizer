import numpy as np
from tqdm import tqdm
import ortools.linear_solver.pywraplp as LPSolving
from ortools.linear_solver.pywraplp import Solver

from .ProblemConfiguration import ProblemConfiguration
import logging


class StorageSelectionProblem:
    def __init__(self, problem_configuration: ProblemConfiguration):
        self.solver: Solver = LPSolving.Solver.CreateSolver('SCIP')
        self.problem_configuration: ProblemConfiguration = problem_configuration
        self.base_variables: dict[str, LPSolving.Variable] = {}
        self.scenario_variables: dict[str, LPSolving.Variable] = {}
        logging.basicConfig(level=logging.DEBUG)



    def buildModel(self):
        logging.debug('building base variables')
        variables = self._buildBaseVariables()
        logging.debug('building scenario variables')
        scenario_variables = self._buildScenarioVariables()
        logging.debug('finished setting up decision variables')

        logging.debug('start setting up constraints')
        self._buildConstraints(variables, scenario_variables)
        logging.debug('finished setting up constraints')

        logging.debug('start setting up objective')
        self._buildObjective(variables, scenario_variables)
        logging.debug('finished setting up objective')

        self.base_variables = variables
        self.scenario_variables = scenario_variables
        logging.debug('finished setting up model')

    def _buildBaseVariables(self) -> dict[str, LPSolving.Variable]:
        numberOfModules = self.solver.IntVar(self.problem_configuration.min_number_of_modules,
                                             self.problem_configuration.max_number_of_modules, 'numberOfModules')
        sizeOfStorageInKwh = self.solver.NumVar(self.problem_configuration.min_storage_size_in_kwh,
                                                self.problem_configuration.max_storage_size_in_kwh,
                                                'sizeOfStorageInKwh')
        return {
            'numberOfModules': numberOfModules,
            'sizeOfStorageInKwh': sizeOfStorageInKwh,
        }

    def _buildScenarioVariables(self) -> dict[str, dict[str, dict[str, LPSolving.Variable]]]:
        variables = {}
        for scenario in range(self.problem_configuration.number_of_scenarios):
            variables[f'scenarioNr_{scenario}'] = self._buildScenarioVariablesForScenario(scenario)
        return variables

    def _buildScenarioVariablesForScenario(self, scenario: int) -> dict[str, dict[str, LPSolving.Variable]]:
        variables = {}
        # we have "configuration_value" days, each day has 24 hours. For each hour we need:
        # a variable to store the amount of energy that is currently in our storage
        # a variable to store the amount of energy the solar panels produce
        # a variable to store the amount of energy we consume (which is overhead but beautiful)
        # a variable to store the amount of energy we need to buy
        # a variable to store the amount of energy we add or take from storage
        # a variable to store the amount of energy we can sell

        for timeslot in range(self.problem_configuration.number_of_days * 24):
            timeslot_name = f'timeslotNr_{timeslot}'
            variables[timeslot_name] = {
                'storageLevel': self.solver.NumVar(0, self.problem_configuration.max_storage_size_in_kwh * 1000, f'{timeslot_name}_storagLevel'),
                'storageEnergyDelta': self.solver.NumVar( -self.problem_configuration.max_storage_size_in_kwh * 1000, self.problem_configuration.max_storage_size_in_kwh * 1000,f'{timeslot_name}_storageEnergyDelta'),
                'producedEnergy': self.solver.NumVar(0, self.solver.Infinity(), f'{timeslot_name}_producedEnergy'),
                'consumedEnergy': self.solver.NumVar(0, self.solver.Infinity(), f'{timeslot_name}_consumedEnergy'),
                'boughtEnergy': self.solver.NumVar(0, self.solver.Infinity(), f'{timeslot_name}_boughtEnergy'),
                'soldEnergy': self.solver.NumVar(0, self.solver.Infinity(), f'{timeslot_name}_soldEnergy'),
            }
        return variables

    def _buildConstraints(self, base_variables: dict[str, LPSolving.Variable],
                          scenario_variables: dict[str, dict[str, LPSolving.Variable]]):
        for scenario in range(self.problem_configuration.number_of_scenarios):
            scenario_name = f'scenarioNr_{scenario}'
            logging.debug(f'processing {scenario_name}')
            current_scenario_variables = scenario_variables[scenario_name]
            self._buildScenarioConstraints(base_variables, current_scenario_variables)

    def _buildScenarioConstraints(self, base_variables, current_scenario_variables):
        # for now, just sample sun intensity from NORM(400, 200) and afterwards min out at 0. Later we should do more clever stuff like a oscillatin (trending) sinus or anything similar
        # this is in Watt / m2, so we need to multiply by the area of the modules to get the total wattage 
        scenario_watt_production = np.random.normal(500, 200, self.problem_configuration.number_of_days * 24)
        scenario_watt_production = np.maximum(scenario_watt_production, 0)
        scenario_watt_production_per_module = scenario_watt_production * self.problem_configuration.area_per_module_in_m2
        scenario_watt_production_per_module = np.minimum(scenario_watt_production_per_module, self.problem_configuration.max_watts_per_module)

        # we use on avg 3kw with standard deviation of 1kw
        scenario_watt_usage = np.random.normal(10000, 2000, self.problem_configuration.number_of_days * 24)
        scenario_watt_usage = np.maximum(scenario_watt_usage, 0)

        # now it gets interesting - im doing this freehand so there might be error - but just letsa go
        # we need to make sure that the amount of energy we store is the amount of energy we produce + the amount of energy we buy - the amount of energy we sell

        # we should write a generator for those slots and names and stuff but anyway
        for timeslot in tqdm(range(self.problem_configuration.number_of_days * 24)):
            timeslot_name = f'timeslotNr_{timeslot}'
            last_timeslot_name = f'timeslotNr_{timeslot - 1}'

            produced_energy = current_scenario_variables[timeslot_name]['producedEnergy']
            # So this makes the produced energy variable equal to the amount of energy produced by the solar panels - easy peasy
            self.solver.Add(produced_energy == scenario_watt_production_per_module[timeslot] * base_variables['numberOfModules'])

            # As I said overhead but a cleaner model
            consumed_energy = current_scenario_variables[timeslot_name]['consumedEnergy']
            self.solver.Add(consumed_energy == scenario_watt_usage[timeslot])

            energy_delta = produced_energy - consumed_energy

            store_energy_delta = current_scenario_variables[timeslot_name]['storageEnergyDelta']
            bought_energy = current_scenario_variables[timeslot_name]['boughtEnergy']
            sold_energy = current_scenario_variables[timeslot_name]['soldEnergy']

            # this seems pretty straight forward
            # we have a delta, that must be equal to the amount sold - the amount bought + the amount stored
            self.solver.Add(energy_delta == sold_energy + store_energy_delta - bought_energy)

            storage_level = current_scenario_variables[timeslot_name]['storageLevel']
            if timeslot == 0:
                # we start with 0 energy in the storage
                self.solver.Add(storage_level == 0)

            if timeslot != 0:
                # we need to make sure that the storage level is the storage level of the last timeslot + the amount of energy we add or take from storage
                self.solver.Add(storage_level == current_scenario_variables[last_timeslot_name][
                    'storageLevel'] + current_scenario_variables[last_timeslot_name][
                    'storageEnergyDelta'])

            # Aaand, we need to at max store the amount of energy we can store - super duper straight forward
            self.solver.Add(storage_level <= base_variables['sizeOfStorageInKwh'] * 1000)

    def _buildObjective(self, base_variables: dict[str, LPSolving.Variable],
                        scenario_variables: dict[str, dict[str, LPSolving.Variable]]):
        # buying costs 50 cts kWh cents, but we could also sample this of course, also per scenario
        energy_purchase_prices = np.random.normal(0.5, 0.0, self.problem_configuration.number_of_days * 24)

        # selling earns 12 cents, but we could also sample this of course, also per scenario
        energy_selling_prices = np.random.normal(0.12, 0.0, self.problem_configuration.number_of_days * 24)

        # now we first calculate the costs in t = 0, which is the costs for buying the solar panels and the storage
        investment = base_variables['numberOfModules'] * self.problem_configuration.price_per_module_in_euro + \
                     base_variables['sizeOfStorageInKwh'] * self.problem_configuration.storage_price_per_kwh_in_euro

        scenario_costs = []
        # now we calculate the costs (or earnings) of each scenario
        logging.debug('start the recourse cost calculation')
        for scenario in tqdm(range(self.problem_configuration.number_of_scenarios)):
            scenario_name = f'scenarioNr_{scenario}'
            current_scenario_variables = scenario_variables[scenario_name]
            scenario_costs.append(self._calculate_scenario_costs(current_scenario_variables, energy_purchase_prices,
                                                                 energy_selling_prices))

        estimated_costs_during_optimization_period = 0
        for scenario_cost in scenario_costs:
            estimated_costs_during_optimization_period += scenario_cost
        estimated_costs_during_optimization_period /= self.problem_configuration.number_of_scenarios

        self.solver.Minimize(investment + estimated_costs_during_optimization_period)

    def _calculate_scenario_costs(self, current_scenario_variables, energy_purchase_prices, energy_selling_prices):
        costs = 0

        # for each timeslot we calculate the costs by multiplying the amount of energy we buy or sell with the purchase/selling price of energy in that timeslot
        for timeslot in range(self.problem_configuration.number_of_days * 24):
            timeslot_name = f'timeslotNr_{timeslot}'
            costs += (energy_purchase_prices[timeslot]) * (current_scenario_variables[timeslot_name]['boughtEnergy'] / 1000)
            costs -= (energy_selling_prices[timeslot]) * (current_scenario_variables[timeslot_name]['soldEnergy'] / 1000)

        return costs
