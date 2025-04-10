import re

texto = " ACABOu BLABLA INJA "

for j in re.search(r"(HOUSING|(?:^| )INJ(?:$| ))", texto).groups():
	print(j)