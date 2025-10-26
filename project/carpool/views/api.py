from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from asgiref.sync import sync_to_async
from carpool.tasks import get_autocompletion, get_routing


@login_required
async def autocompletion(request) -> JsonResponse:
    """
    An async API proxy endpoint to get latitude and
    longitude for a given query.
    """
    text = request.GET.get("text", "")
    if not text:
        return JsonResponse({"status": "NOK"}, status=400)

    task = get_autocompletion.delay(text)
    result = await sync_to_async(task.get)(timeout=5)  # blocking I/O offloaded
    return JsonResponse({"status": "OK", "results": result}, safe=False, status=200)


@login_required
async def routing(request) -> JsonResponse:
    """
    An async API proxy endpoint to get routing information.
    """
    start = request.GET.get("start", "")
    end = request.GET.get("end", "")
    intermediates = request.GET.getlist("intermediates", [])
    print(intermediates)

    if not start or not end:
        return JsonResponse({"status": "NOK"}, status=400)
    task = get_routing.delay(start, end, intermediates)
    res = await sync_to_async(task.get)(timeout=5)  # blocking I/O offloaded
    return JsonResponse(res, safe=False)
