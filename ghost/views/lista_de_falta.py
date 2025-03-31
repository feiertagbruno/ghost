from django.shortcuts import render

def lista_de_falta(request):
    context = {
        "caller":"lista_de_falta"
    }
    return render(request, "ghost/listadefalta/listadefalta.html", context)

def lista_de_falta_post(request):
    context = {
        "caller": "lista_de_falta_post"
    }
    return render(request, "ghost/listadefalta/listadefalta.html", context)