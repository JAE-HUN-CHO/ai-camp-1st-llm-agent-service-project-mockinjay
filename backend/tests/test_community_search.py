from app.api.community import router


def test_community_search_route_is_registered():
    routes = {
        (route.path, method)
        for route in router.routes
        for method in route.methods
    }

    assert ("/search", "GET") in routes
