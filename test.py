from generative_philter_surrogates import Scrubber

s = Scrubber()
with open("/home/mike/code/ctakes-examples/ctakes_examples/resources/curated/psychiatric-evaluation-4.txt", "r") as f:
    print(s.scrub_text(f.read()))
