

class ProblemConfiguration:
    def __init__(self):
        self.max_watts_per_module = 800
        self.area_per_module_in_m2 = 1.2
        self.price_per_module_in_euro = 670
        self.max_number_of_modules = 100
        self.min_number_of_modules = 0

        self.storage_price_per_kwh_in_euro = 1400
        self.min_storage_size_in_kwh = 0
        self.max_storage_size_in_kwh = 1000

        self.number_of_scenarios = 10

        self.number_of_days = 365
