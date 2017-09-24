import subprocess


class StanfordServer:
    def __init__(self, jar_path: str = './lib/stanford-postagger.jar',
                 model_path: str = './lib/english-left3words-distsim.tagger', port: int = 5000) -> None:
        super().__init__()
        self.port = port
        self.jar_path = jar_path
        self.classpath = 'edu.stanford.nlp.tagger.maxent.MaxentTaggerServer'
        self.model_path = model_path

    def __enter__(self):
        # Start Stanford Server
        print('Starting Stanford Server on Port %d ...' % self.port, end='', flush=True)
        self.subprocess = subprocess.Popen(
            ['java', '-mx500m', '-cp', self.jar_path, self.classpath, '-model', self.model_path, '-port',
             str(self.port), '-sentenceDelimiter', 'newline', '-tokenize', 'false'], stderr=subprocess.STDOUT,
            stdout=subprocess.PIPE)
        status = True
        # Wait while Server is Started, or terminate if error occurred
        try:
            out = self.subprocess.communicate(timeout=4)[0].decode('ascii')
            status = False
            print('... ERROR!')
            print(out)
        except subprocess.TimeoutExpired:
            # wait until some console output is given
            pass
        if status:
            print('... DONE!')
        else:
            self.subprocess.terminate()
            exit(0)

    def __exit__(self, type, value, traceback):
        # Terminate Server Process
        self.subprocess.terminate()
