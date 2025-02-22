a = {
	"b": [{"abc":1},{"cde":2}],
	"c": [{"abc":1},{"cde":3}]
}

print(a["b"][len(a["b"])-1]["cde"])