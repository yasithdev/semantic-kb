import subprocess
import time


class StanfordServer:
    def __init__(self, jar_path: str = './lib/stanford-postagger.jar',
                 model_path: str = './lib/english-bidirectional-distsim.tagger', port: int = 5000) -> None:
        super().__init__()
        self.port = port
        self.jar_path = jar_path
        self.classpath = 'edu.stanford.nlp.tagger.maxent.MaxentTaggerServer'
        self.model_path = model_path

    def __enter__(self):
        # Start Stanford Server
        print('Starting Stanford Server on Port %d' % self.port)
        self.subprocess = subprocess.Popen(
            ['java', '-mx300m', '-cp', self.jar_path, self.classpath, '-model', self.model_path, '-port',
             str(self.port)])
        # Wait while Server is Started.
        time.sleep(3)
        print('Stanford Server Started Successfully')

    def __exit__(self, type, value, traceback):
        # Terminate Server Process
        self.subprocess.terminate()
