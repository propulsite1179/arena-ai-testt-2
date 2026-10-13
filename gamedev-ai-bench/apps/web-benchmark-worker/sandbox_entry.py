from pathlib import Path
from gamedev.services.evaluator import evaluate
if __name__=='__main__':
    evaluate(Path('/project'),Path('/output'))
