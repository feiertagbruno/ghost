import pandas as pd

# DataFrame com MultiIndex nas colunas
arrays = [
    ['A', 'A', 'B', 'B'],
    ['2025-02-18', '2025-02-19', '2025-02-18', '2025-02-19']
]
multi_index = pd.MultiIndex.from_arrays(arrays, names=('Categoria', 'Data'))

df1 = pd.DataFrame({
    ('A', '2025-02-18'): [1, 2],
    ('A', '2025-02-19'): [3, 4],
    ('B', '2025-02-18'): [5, 6],
    ('B', '2025-02-19'): [7, 8]
}, columns=multi_index, index=['X', 'Y'])

# Outro DataFrame com MultiIndex nas colunas
df2 = pd.DataFrame({
    ('A', '2025-02-18'): [10, 20],
    ('A', '2025-02-19'): [30, 40],
    ('B', '2025-02-18'): [50, 60],
    ('B', '2025-02-19'): [70, 80]
}, columns=multi_index, index=['X', 'Y'])

# Visualizando df1 e df2
print("df1:")
print(df1)
print("\ndf2:")
print(df2)