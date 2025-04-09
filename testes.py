from pandas import DataFrame

a = DataFrame({"a":[1,2,3,4,5],"b":[1,1,1,2,2]})

b = a.loc[a["b"] == 2,:]
for i, val in b.iterrows():
	a.at[i,"a"] = 6

print(a)