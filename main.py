from optimization.ProblemConfiguration import ProblemConfiguration
from optimization.StorageSelectionProblem import StorageSelectionProblem

if __name__ == '__main__':
    configuration = ProblemConfiguration()

    # Edit configuration if you want
    # The parameters are volatile - if you want more realistic stuff you need to change scenario sampling (for solar input) and energy costs sampling.
    # The following values are not very realistic, but chosen so that the MILP Solver is actually doing magic trickery
    # Keep close to this or at least be mindful or the solution will be very clear.. (some of the provided bounds)

    # of course the number of days etc also plays an important role, becaus the more days - the more chance for storage to be useful ...

    configuration.number_of_scenarios = 5
    configuration.min_storage_size_in_kwh = 0
    configuration.max_storage_size_in_kwh = 100
    configuration.min_number_of_modules = 0
    configuration.max_number_of_modules = 200
    configuration.number_of_days = 365

    configuration.storage_price_per_kwh_in_euro = 50
    configuration.price_per_module_in_euro = 850

    problem = StorageSelectionProblem(configuration)
    problem.buildModel()
    problem.solver.EnableOutput()
    print('Starting to solve problem. Problem characteristics:')
    print('variables:', problem.solver.NumVariables())
    print('constraints:', problem.solver.NumConstraints())
    # delete old file if it exists
    with open('model.txt', 'w+') as file:
        file.truncate(0)
        file.write(problem.solver.ExportModelAsLpFormat(False))
    problem.solver.Solve()

    print('Modules:', problem.base_variables['numberOfModules'].solution_value())

    print('Storage:', problem.base_variables['sizeOfStorageInKwh'].solution_value())
