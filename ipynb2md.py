"""
A simple, fast, beautiful tool to convert jupyter notebook to markdown.

Author: Cloudy1225

References:
     1. https://nbformat.readthedocs.io/en/latest/index.html
     2. https://nbconvert.readthedocs.io/en/latest/index.html
"""


import os
import errno
import argparse
import base64
import json
import re
from typing import List


class Config:
    input_file = None
    output_file = None
    image_dir_name = None
    image_base_path = None

    in_prompt_color = '#303f9f'
    out_prompt_color = '#d84315'

    stdout_background = '#eaeef2'
    stderr_background = '#fddfdd'

    error_background = '#fddfdd'

    display_data_priority = [
        "text/html",
        "text/markdown",
        "image/svg+xml",
        "text/latex",
        "image/png",
        "image/jpeg",
        "text/plain",
    ]

    @staticmethod
    def set_file_path(in_fp: str):
        """
        Set the file path of Config.

        Parameters
        ----------
        in_fp : str
            The file path of the notebook.
        """
        in_fp = os.path.normpath(in_fp)  # Normalize the pathname
        Config.input_file = in_fp
        dir_name = os.path.dirname(in_fp)
        base_name = os.path.basename(in_fp)
        out_name = base_name.split('.')
        out_name.pop()
        Config.image_dir_name = '.'.join(out_name) + '_images'
        Config.image_base_path = os.path.join(dir_name, Config.image_dir_name)
        out_name.append('md')
        md_name = '.'.join(out_name)
        Config.output_file = os.path.join(dir_name, md_name)


class NotJSONError(ValueError):
    pass


class UnknownOutputError(ValueError):
    pass


def read(fp: str) -> dict:
    """
    Read a notebook from a file as a dict.
    Notebook format errors will be logged.

    Parameters
    ----------
    fp : str
        The file path of the notebook.

    Returns
    -------
    nb : dict
        The notebook that was read.

    Raises
    ------
    NotJSONError
        The notebook is not with JSON schema.
    """
    input_stream = open(fp, 'r', encoding='utf-8')
    try:
        nb = json.load(input_stream)
    except ValueError as e:
        raise NotJSONError('Notebook does not appear to be JSON :(') from e
    print('Successfully load the notebook as a dict from %r :)' % fp)
    return nb


def write(fp: str, md: str):
    """
    Write the converted markdown file.

    Parameters
    ----------
    fp : str
        The file path of the markdown file.

    md : str
        The string-like content of the markdown file.
    """
    with open(fp, 'w', encoding='utf-8') as f:
        f.write(md)
    print('Successfully save the converted markdown file to %r :)' % fp)


class MarkdownCreator:
    """
    Util to create markdown-syntax string block.
    """

    @staticmethod
    def create_code_block(code: str, language: str = 'python') -> str:
        """
        Create a markdown code block.
        Usually used to convert code cells of the notebook.

        Parameters
        ----------
        code : str
            Source code in the code block.
        language: str, Default='python'
            The language of source code.

        Returns
        -------
        s : str
            The markdown-syntax string of created code block.
        """
        prefix = '```'
        if language is not None:
            prefix += language
        return prefix + '\n' + code + '\n```'

    @staticmethod
    def create_in_prompt() -> str:
        return '<p style="color: %s;"><b>In:</b></p>\n' % Config.in_prompt_color

    @staticmethod
    def create_out_prompt() -> str:
        return '<p style="color: %s;"><b>Out:</b></p>\n' % Config.out_prompt_color

    @staticmethod
    def create_stream_block(text: List[str], name: str) -> str:
        """
        Create a html-syntax block to wrap the stream output in the notebook.

        Parameters
        ----------
        text : List[str]
            List of output lines
        name: str, Default='python'
            The name of the stream:
            "stdout": background color is default #eaeef2
            "stderr": background color is default #fddfdd
        Returns
        -------
        s : str
            The markdown-syntax string of created block.
        """
        background_color = Config.stdout_background
        if name == 'stderr':
            background_color = Config.stderr_background
        prefix = '<pre style="background: %s; padding-top: 5px">\n' % background_color
        content = ''.join(text)
        content = re.sub('<', '&lt;', content)
        content = re.sub('\n', '&#xA;', content)
        suffix = '</pre>'
        return prefix + content + suffix

    @staticmethod
    def create_error_block(traceback_str: str) -> str:
        """
        Create a html-syntax block to wrap the error output in the notebook.

        Parameters
        ----------
        traceback_str : str
            The traceback string.

        Returns
        -------
        s : str
            The markdown-syntax string of created block.
        """
        background_color = Config.error_background
        prefix = '<pre style="background: %s; padding-top: 5px">\n' % background_color
        content = ''.join(traceback_str)
        content = re.sub('<', '&lt;', content)
        content = re.sub('\n', '&#xA;', content)
        suffix = '</pre>'
        return prefix + content + suffix

    @staticmethod
    def create_html_block(raw_html: str) -> str:
        """
        Create a html-syntax block to wrap the html output in the notebook.

        Parameters
        ----------
        raw_html : str
            The html string.

        Returns
        -------
        s : str
            The markdown-syntax string of created block.
        """
        return re.sub('\n', '&#xA;', raw_html) + '\n'
        # return re.sub('\n{2,}', '\n', raw_html) + '\n'

    @staticmethod
    def create_image_block(image_path: str) -> str:
        """
        Create a markdown-syntax block to wrap the image output in the notebook.

        Parameters
        ----------
        image_path : str
            The relative path of image.

        Returns
        -------
        s : str
            The markdown-syntax string of created block.
        """
        return '![](./%s)' % image_path


def ensure_dir_exists(path, mode=0o755):
    """ensure that a directory exists

    If it doesn't exist, try to create it and protect against a race condition
    if another process is doing the same.

    The default permissions are 755, which differ from os.makedirs default of 777.
    """
    if not os.path.exists(path):
        try:
            print("Making directory %r to save images :)" % path)
            os.makedirs(path, mode=mode)
        except OSError as e:
            if e.errno != errno.EEXIST:
                raise
    elif not os.path.isdir(path):
        raise OSError("%r exists but is not a directory :(" % path)


class OutputsParser:
    """
    Util to parse outputs of code cells in a notebook.
    """

    def __init__(self, outputs: List[dict]):
        self.outputs = outputs

    @staticmethod
    def parse_error(traceback: List[str]) -> str:
        raw_str = '\n'.join(traceback)
        # Remove ANSI escape codes from text.
        _ANSI_RE = re.compile("\x1b\\[(.*?)([@-~])")
        pure_str = _ANSI_RE.sub("", raw_str)
        return MarkdownCreator.create_error_block(pure_str)

    # the number of the base64-format images
    # used to save the base64-format images
    image_count = 0

    @staticmethod
    def write_image(base64_str, image_path):
        base64_bytes = base64_str.encode("ascii")
        raw_bytes = base64.decodebytes(base64_bytes)
        with open(image_path, 'wb') as f:
            f.write(raw_bytes)

    @staticmethod
    def parse_display_data(data: dict):
        display_data_priority = Config.display_data_priority
        MAX = 100
        min_index = MAX
        for mime_type in data.keys():
            try:
                cur_index = display_data_priority.index(mime_type)
            except ValueError:
                continue
            if cur_index < min_index:
                min_index = cur_index
        if min_index == MAX:
            raise UnknownOutputError("Output's MIME type must be one of %s :(" % str(display_data_priority))
        mime_type = display_data_priority[min_index]
        raw_content = data[mime_type]
        if mime_type == 'text/html':
            # Replace several continuous linefeed with only one
            # otherwise the markdown renderer seems not to render it correctly
            return MarkdownCreator.create_html_block(raw_content)
        elif mime_type.startswith('text'):  # except 'text/html'
            return raw_content
        else:  # extract images
            image_type = mime_type.split('/')[1]
            if image_type.startswith('svg'):
                image_type = 'svg'
            OutputsParser.image_count += 1
            image_name = 'image%i.%s' % (OutputsParser.image_count, image_type)
            base_path = Config.image_base_path
            # Make a directory if it doesn't already exist
            if base_path:
                ensure_dir_exists(base_path)
            image_path = os.path.join(base_path, image_name)
            OutputsParser.write_image(raw_content, image_path)
            relative_path = os.path.join(Config.image_dir_name, image_name)
            relative_path = '/'.join(os.path.split(relative_path))
            return MarkdownCreator.create_image_block(relative_path)

    def to_md(self) -> List[str]:
        outputs_md = []
        for output in self.outputs:
            output_type = output['output_type']  # stream, display_data, execute_result or error
            if output_type == 'stream':
                name = output['name']  # stdout or stderr
                text = output['text']  # content of stream output
                outputs_md.append(MarkdownCreator.create_stream_block(text, name))
            elif output_type == 'error':
                traceback = output['traceback']
                outputs_md.append(self.parse_error(traceback))
            else:  # display_data / execute_result
                data = output['data']
                outputs_md.append(self.parse_display_data(data))
        return outputs_md


def parse_convert(nb: dict) -> str:
    """
    Parse a notebook and convert it to markdown.

    Parameters
    ----------
    nb : dict
        The dict-like notebook.

    Returns
    -------
    md : str
        The converted markdown string.
    """
    md = []  # list containing str of lines
    cells = nb['cells']  # list of cell dictionaries in a notebook.
    for cell in cells:
        cell_type = cell['cell_type']  # 'code', 'markdown' or 'raw'
        src = ''.join(cell['source'])  # source code
        if cell_type == 'code':
            md.append(MarkdownCreator.create_in_prompt())  # 'In'

            # create a markdown block to wrap the source code
            src_md_block = MarkdownCreator.create_code_block(src)
            md.append(src_md_block)

            # parse outputs
            outputs = cell['outputs']
            if len(outputs) != 0:
                md.append(MarkdownCreator.create_out_prompt())  # 'Out'
            outputs_md = OutputsParser(outputs).to_md()
            md.extend(outputs_md)

        else:  # markdown or raw: convert directly
            md.append(src + '\n')

    return '\n'.join(md)


if __name__ == '__main__':
    # parse the argument from console
    parser = argparse.ArgumentParser()
    parser.add_argument("fp", help="file path of the notebook")
    args = parser.parse_args()
    fp = args.fp
    Config.set_file_path(fp)

    # main
    nb = read(fp=Config.input_file)
    md = parse_convert(nb)
    write(fp=Config.output_file, md=md)
