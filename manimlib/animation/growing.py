from manimlib.web.utils import serialize_args, serialize_config
from manimlib.animation.transform import Transform
# from manimlib.utils.paths import counterclockwise_path
from manimlib.constants import PI


class GrowFromPoint(Transform):
    CONFIG = {
        "point_color": None,
    }

    def __init__(self, mobject, point, **kwargs):
        if not hasattr(self, "args"):
            self.args = serialize_args([mobject, point])
        if not hasattr(self, "config"):
            self.config = serialize_config({
                **kwargs,
            })
        self.point = point
        super().__init__(mobject, **kwargs)

    def create_target(self):
        return self.mobject

    def create_starting_mobject(self):
        start = super().create_starting_mobject()
        start.scale(0)
        start.move_to(self.point)
        if self.point_color:
            start.set_color(self.point_color)
        return start


class GrowFromCenter(GrowFromPoint):
    def __init__(self, mobject, **kwargs):
        if not hasattr(self, "args"):
            self.args = serialize_args([mobject])
        if not hasattr(self, "config"):
            self.config = serialize_config({
                **kwargs,
            })
        point = mobject.get_center()
        super().__init__(mobject, point, **kwargs)


class GrowFromEdge(GrowFromPoint):
    def __init__(self, mobject, edge, **kwargs):
        if not hasattr(self, "args"):
            self.args = serialize_args([mobject, edge])
        if not hasattr(self, "config"):
            self.config = serialize_config({
                **kwargs,
            })
        point = mobject.get_critical_point(edge)
        super().__init__(mobject, point, **kwargs)


class GrowArrow(GrowFromPoint):
    def __init__(self, arrow, **kwargs):
        if not hasattr(self, "args"):
            self.args = serialize_args([arrow])
        if not hasattr(self, "config"):
            self.config = serialize_config({
                **kwargs,
            })
        point = arrow.get_start()
        super().__init__(arrow, point, **kwargs)


class SpinInFromNothing(GrowFromCenter):
    CONFIG = {
        "path_arc": PI,
    }
