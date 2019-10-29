def animation_to_json(play_args, play_kwargs):
    animation = play_args[0]
    return {
      "className": animation.__class__.__name__,
      "args": animation.get_args(),
      "durationSeconds": animation.run_time,
    }
