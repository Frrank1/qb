from luigi import LocalTarget, Task, WrapperTask, ExternalTask
from qanta.util.io import shell
import qanta.util.constants as c
from qanta.extractors import mentions


class NLTKDownload(ExternalTask):
    def output(self):
        return LocalTarget('data/external/nltk_download_SUCCESS')


class CompileCLM(ExternalTask):
    def output(self):
        return LocalTarget('clm/_SUCCESS')


class Wikipedia(Task):
    def requires(self):
        CompileCLM()

    def run(self):
        shell('mkdir -p data/external/wikipedia')
        shell('python3 cli.py init_wiki_cache data/external/wikipedia')
        shell('touch data/external/wikipedia_SUCCESS')

    def output(self):
        return LocalTarget('data/external/wikipedia_SUCCESS')


class DownloadData(WrapperTask):
    def requires(self):
        yield NLTKDownload()
        yield Wikipedia()


class KenLM(Task):
    def requires(self):
        yield DownloadData()

    def run(self):
        shell('mkdir -p temp')
        shell('mkdir -p output')
        mentions.build_lm_data('/tmp/wikipedia_sentences')
        shell('lmplz -o 5 < /tmp/wikipedia_sentences > /tmp/kenlm.arpa')
        shell('build_binary /tmp/kenlm.arpa {}'.format(c.KEN_LM))
        shell('rm /tmp/wikipedia_sentences /tmp/kenlm.arpa')

    def output(self):
        return LocalTarget(c.KEN_LM)


class WikifierInput(Task):
    def requires(self):
        yield DownloadData()

    def run(self):
        shell('rm -rf {}'.format(c.WIKIFIER_INPUT_TARGET))
        shell('mkdir -p {}'.format(c.WIKIFIER_INPUT_TARGET))
        shell('python3 cli.py wikify {}/'.format(c.WIKIFIER_INPUT_TARGET))
        shell('touch {}/_SUCCESS'.format(c.WIKIFIER_INPUT_TARGET))

    def output(self):
        return LocalTarget('{}/_SUCCESS'.format(c.WIKIFIER_INPUT_TARGET))


class WikifierOutput(Task):
    def requires(self):
        yield WikifierInput()

    def run(self):
        shell('rm -rf {}'.format(c.WIKIFIER_OUTPUT_TARGET))
        shell('mkdir -p {}'.format(c.WIKIFIER_OUTPUT_TARGET))
        command = (
            '(cd data/external/Wikifier2013 '
            '&& java -Xmx10G -jar dist/wikifier-3.0-jar-with-dependencies.jar '
            '-annotateData '
            '../../../{} '
            '../../../{} '
            'false configs/STAND_ALONE_NO_INFERENCE.xml)'
        )
        shell(command.format(c.WIKIFIER_INPUT_TARGET, c.WIKIFIER_OUTPUT_TARGET))
        shell('touch {}/_SUCCESS'.format(c.WIKIFIER_OUTPUT_TARGET))

    def output(self):
        return LocalTarget('{}/_SUCCESS'.format(c.WIKIFIER_OUTPUT_TARGET))


class Preprocess(WrapperTask):
    def requires(self):
        yield KenLM()
