import pandas as pd

b = pd.DataFrame({"abc":["a","b","c"]})
for i in enumerate(b.columns):
    print(i)