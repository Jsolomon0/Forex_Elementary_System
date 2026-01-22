
import optuna
from optimizer import objective_ind
import time
from back_test import opt_ind_test


study = optuna.create_study(direction="maximize")
study.optimize(objective_ind, n_trials=100)

print("Best Parameters found:")
test_params = study.best_params
print(test_params)

time.sleep(20)

print("Running backtest with best parameters...")
time.sleep(5)


maxing = opt_ind_test(test_params['atr_p'],
            test_params['ema_f'], 
            test_params['ema_s'], 
            test_params['adx_p'], 
            test_params['z_p'], 
            test_params['atr_z_p']
            )

print(maxing)  
