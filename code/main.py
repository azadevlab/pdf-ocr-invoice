import os.path, re, time
from warnings import filterwarnings
from yaml import load as yl, FullLoader as yfl 
from requests import get as reqget
from argparse import ArgumentParser
from math import ceil
from easyocr import Reader
from fitz import open as fitz_o
from bs4 import BeautifulSoup as bs
from tabulate import tabulate
from functools import reduce


filterwarnings("ignore", category=UserWarning)
script_path = os.path.dirname(os.path.realpath(__file__))
config_file = os.path.join(script_path, "config.yml")
with open(config_file, "r") as ymlfile:
    config = yl(ymlfile, Loader=yfl)

arg_parser = ArgumentParser()
arg_parser.add_argument("invoice_pdf", nargs=1, \
    help="Обязательный аргумент. Указываем имя pdf файла инвойса")
arg_parser.add_argument("zarplata", nargs="?", type=int, \
    default=config["tax"]["mzp"]["min"], \
    help="Необязательный аргумент. Указываем Зарплату в тенге только в цифрах и без пробела")

invoice_pdf = arg_parser.parse_args().invoice_pdf
zarplata = arg_parser.parse_args().zarplata
if zarplata < int(config["tax"]["mzp"]["min"]):
    zarplata = int(config["tax"]["mzp"]["min"])
    print(f"ЗарПлата не может быть меньше МЗП, теперь ЗП: {zarplata}")


def stopwatch(func):
    """
    decorator shows execution time of function/def
    """
    def wrapper(*args, **kwargs):
        start_time = time.time()
        result = func(*args, **kwargs)
        print(f"{func.__name__} def been executed in: {(time.time() - start_time)}")
        return result
    return wrapper

def exchange_rate(http_url: dict):
    """
    get exchanged rate on invoice date
    """
    soup_class = "table table-bordered table-striped text-size-xs"
    response = http_url["http"] + http_url["select_currency"] + "&beginDate=" + invoice_date + "&endDate=" + invoice_date
    soup = bs(reqget(response).text, "html")
    exchange_rate_kzt = float(soup.find("table", class_=soup_class).find_all("td")[-1].text)
    return exchange_rate_kzt

def aza_summary(*args):
    return reduce(lambda x, y: x+y, args)

def thousands_separator(numbers):
    """
    convert to string and separate thousands by space
    """
    converted_strings = str("{0:,}".format(int(numbers)).replace(",", " "))
    return converted_strings

@stopwatch
def pdf_2_text(file_name: str):
    """
    convert pdf to image and then using OCR create recognized text lists
    """
    text_recognized_list = []
    with open(file_name, "rb") as aza_pdf:
        pages = fitz_o(aza_pdf)
        for page in pages:
            aza_picture = page.get_pixmap(dpi = 300)
            text_recognized_list.append(Reader(["ru", "en"]).readtext(aza_picture.tobytes(), detail=0))
    return text_recognized_list

@stopwatch
def create_global_vars(file_list: list, conf_dict: dict):
    """
    create variables from recognized text by regex nested dict in config_dict
    """
    for key, value in conf_dict.items():
        regex_filter = value.get("regex")
        if "extra_global_var" in value:
            globals()[key] = eval(value.get("formula"))
        if "regex" in value:
            globals()[key] = "".join(re.findall(regex_filter, str(file_list)))
        if "replacer" in value:
            for k, v in value.get("replacer").items():
                globals()[key] = re.sub(k, v, globals()[key], flags=re.IGNORECASE)
        if "type" in value:
            globals()[key] = eval(value.get("type"))(globals()[key])

@stopwatch
def total_tabulate(dict_: dict):
    """ 
    using tabulate to print humanreadble by block
    """
    aza_list_nested_list = []
    for key, value in dict_.items():      
        if "local_variables_create" in value:
            aza_local_vars = list(value)
            ### only if you`re not lazy and wanna filter which local var to create
            ### you need list keys in local_variables_create = {local_variables_create: min, formula, etc}
            # aza_local_vars = re.sub("[^\w]", " ", value.get("local_variables_create")).split()
            for i in aza_local_vars:
                try:
                    locals()[f"local_{key}_{i}"] = eval(value.get(i))
                except:
                    locals()[f"local_{key}_{i}"] = value.get(i)

        if "header" in key:
            aza_list_nested_list.append(list(value.values()))
            aza_header_keys = list(value.keys())

        if "header" not in key:
            aza_tmp_innerlist = []
            for i in aza_header_keys:
                try:
                    aza_tmp_innerlist.append(eval(value.get(i)))
                except:
                    aza_tmp_innerlist.append(value.get(i))
            aza_list_nested_list.append(aza_tmp_innerlist)

    print(tabulate(aza_list_nested_list, headers="firstrow", tablefmt="fancy_grid"))


if __name__ == "__main__":
    start_time = time.time()
    for invoice_pdf in invoice_pdf:
        in_file = os.path.abspath(invoice_pdf)
        if not os.path.exists(in_file):
            invoice_pdf = input("Invoice PDF not found! Please enter the correct file name: ")
    create_global_vars(pdf_2_text(invoice_pdf), config["pdf_vars"])
    for d in (config["pdf_vars"], config["esf"], config["tax"]): total_tabulate(d)
    print(f"total execution time: {(time.time() - start_time)}")
