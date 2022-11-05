# ipynb2md

A simple, fast and beautiful tool to convert jupyter notebook to markdown file.



## Introduction

I want to used markdown to display notebook in my blog. But the official nbconvert did not satisfy me.  Therefore, I customized  this `ipynb2md`.

You can see examples [here](example) . There are three markdown file in the example directory. They are conversion results of `example.ipynb`：

- `example_ipynb2md.md`: by ipynb2md
- `example_nbconvert.md`: by [nbconvert](https://nbconvert.readthedocs.io/en/latest/index.html)
- `eaxmple_vertopal.md`: by [vertopal](https://www.vertopal.com/)

Since Github can not render markdown with color, you can copy the markdown raw code, and have a look on your own markdown renderer like VSCode.



**ipynb2md vs nbconvert --to markdown**：

- Advantages:
  1. This does not require any third-party libraries.
  2. This is faster than official nbconvert.
  3. This looks more like the source notebook by adding more html blocks.
- Disadvantages:
  1. This only has one function: convert `.ipynb` to `.md`
  2. This is not convenient because you can just use it by passing the `.ipynb` file path.



## Install

Just copy the source code of `ipynb2md.py`.

Or clone this repository to have a test of `eaxmple.ipynb`.



## Use it

In console: 

```bash
python ipynb2md.py example/example.ipynb
```
