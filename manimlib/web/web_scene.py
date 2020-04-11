from manimlib.scene.scene import PyScene


class Scene(PyScene):
    def __init__(self, **kwargs):
        self.init_kwargs = kwargs

    def render(self):
        # PyScene renders upon instantiation.
        return super(Scene, self).__init__(**self.init_kwargs)
