import json
import logging
import os
import xml.etree.ElementTree as ET
from typing import Tuple

MARKDOWN_SUFFIX = ".md"


class XmlElementConvert(object):
    """
    XML Element 转换规则
    """

    @staticmethod
    def convert_para_func(**kwargs):
        """正常文本（粗体、斜体、删除线、链接）"""
        return kwargs.get("text")

    @staticmethod
    def convert_heading_func(**kwargs):
        """标题"""
        level = kwargs.get("element").attrib.get("level", 0)
        level = 1 if level in (["a", "b"]) else level
        text = kwargs.get("text")
        return " ".join(["#" * int(level), text]) if text else text

    @staticmethod
    def convert_image_func(**kwargs):
        """图片"""
        image_url = XmlElementConvert.get_text_by_key(
            list(kwargs.get("element")), "source"
        )
        return "![{text}]({image_url})".format(
            text=kwargs.get("text"), image_url=image_url
        )

    @staticmethod
    def convert_attach_func(**kwargs):
        """附件"""
        element = kwargs.get("element")
        filename = XmlElementConvert.get_text_by_key(list(element), "filename")
        resource_url = XmlElementConvert.get_text_by_key(list(element), "resource")
        return "[{text}]({resource_url})".format(
            text=filename, resource_url=resource_url
        )

    @staticmethod
    def convert_code_func(**kwargs):
        """代码块"""
        language = XmlElementConvert.get_text_by_key(
            list(kwargs.get("element")), "language"
        )
        return "```{language}\r\n{code}```".format(
            language=language, code=kwargs.get("text")
        )

    @staticmethod
    def convert_todo_func(**kwargs):
        """to-do"""
        return "- [ ] {text}".format(text=kwargs.get("text"))

    @staticmethod
    def convert_quote_func(**kwargs):
        """引用"""
        return "> {text}".format(text=kwargs.get("text"))

    @staticmethod
    def convert_horizontal_line_func(**kwargs):
        """分割线"""
        return "---"

    @staticmethod
    def convert_list_item_func(**kwargs):
        """列表"""
        list_id = kwargs.get("element").attrib["list-id"]
        is_ordered = kwargs.get("list_item").get(list_id)
        text = kwargs.get("text")
        if is_ordered == "unordered":
            return "- {text}".format(text=text)
        elif is_ordered == "ordered":
            return "1. {text}".format(text=text)

    @staticmethod
    def convert_table_func(**kwargs):
        """
        表格转换
        :param kwargs:
        :return:
        """
        element = kwargs.get("element")
        content = XmlElementConvert.get_text_by_key(element, "content")

        table_data_str = f""  # f-string 多行字符串
        nl = "\r\n"  # 考虑 Windows 系统，换行符设为 \r\n
        table_data = json.loads(content)
        table_data_len = len(table_data["widths"])
        table_data_arr = []
        table_data_line = []

        for cells in table_data["cells"]:
            values = cells.get("value")
            if values is None:
                values = ""
            cell_value = XmlElementConvert._encode_string_to_md(values)
            table_data_line.append(cell_value)
            # 攒齐一行放到 table_data_arr 中，并重置 table_data_line
            if len(table_data_line) == table_data_len:
                table_data_arr.append(table_data_line)
                table_data_line = []

        # 如果只有一行，那就给他加一个空白 title 行
        if len(table_data_arr) == 1:
            table_data_arr.insert(0, [ch for ch in (" " * table_data_len)])
            table_data_arr.insert(1, [ch for ch in ("-" * table_data_len)])
        elif len(table_data_arr) > 1:
            table_data_arr.insert(1, [ch for ch in ("-" * table_data_len)])

        for table_line in table_data_arr:
            table_data_str += "|"
            for table_data in table_line:
                table_data_str += f" %s |" % table_data
            table_data_str += f"{nl}"

        return table_data_str

    @staticmethod
    def get_text_by_key(element_children, key="text"):
        """
        获取文本内容
        :return:
        """
        for sub_element in element_children:
            if key in sub_element.tag:
                return sub_element.text if sub_element.text else ""
        return ""

    @staticmethod
    def _encode_string_to_md(original_text):
        """将字符串转义防止 markdown 识别错误"""
        if len(original_text) <= 0 or original_text == " ":
            return original_text

        original_text = original_text.replace("\\", "\\\\")  # \\ 反斜杠
        original_text = original_text.replace("*", "\\*")  # \* 星号
        original_text = original_text.replace("_", "\\_")  # \_ 下划线
        original_text = original_text.replace("#", "\\#")  # \# 井号

        # markdown 中需要转义的字符
        original_text = original_text.replace("&", "&amp;")
        original_text = original_text.replace("<", "&lt;")
        original_text = original_text.replace(">", "&gt;")
        original_text = original_text.replace("“", "&quot;")
        original_text = original_text.replace("‘", "&apos;")

        original_text = original_text.replace("\t", "&emsp;")

        # 换行 <br>
        original_text = original_text.replace("\r\n", "<br>")
        original_text = original_text.replace("\n\r", "<br>")
        original_text = original_text.replace("\r", "<br>")
        original_text = original_text.replace("\n", "<br>")

        return original_text


class JsonConvert(object):
    """
    json 转换规则
    """

    def _get_common_text(self, content: dict) -> str:
        """递归提取节点中的纯文本内容，安全版"""
        if not isinstance(content, dict):
            return ""

        # 如果节点本身有 '8' 字段，直接取
        if "8" in content:
            raw = content.get("8", "")
            # 如果有 '9' 样式属性，应用样式
            if "9" in content and raw:
                raw = self._convert_text_attribute(raw, content["9"])
            return raw

        all_text = ""
        # 如果有 '7' 字段，遍历提取
        if "7" in content and isinstance(content["7"], list):
            for item in content["7"]:
                if isinstance(item, dict) and "8" in item:
                    raw = item.get("8", "")
                    if "9" in item and raw:
                        raw = self._convert_text_attribute(raw, item["9"])
                    all_text += raw
            return all_text

        # 递归处理 '5' 子节点
        if "5" in content and isinstance(content["5"], list):
            for child in content["5"]:
                if isinstance(child, dict):
                    all_text += self._get_common_text(child)
        return all_text

    def _convert_text_attribute(self, text: str, text_attrs: list):
        """文本属性（粗体、斜体）"""
        if not text or not isinstance(text_attrs, list):
            return text
        for attr in text_attrs:
            if isinstance(attr, dict) and attr.get("2") == "b":
                text = f"**{text}**"
            elif isinstance(attr, dict) and attr.get("2") == "i":
                text = f"*{text}*"
        return text

    def convert_text_func(self, content) -> str:
        """正常文本、粗体、斜体、删除线、链接"""
        all_text = ""
        one_five_contents = content.get("5", [])
        for one_five_content in one_five_contents:
            if not isinstance(one_five_content, dict):
                continue
            two_five_contents = one_five_content.get("5", [])
            text_type = one_five_content.get("6")
            seven_contents = one_five_content.get("7", [])

            if seven_contents and not two_five_contents:
                text = ""
                for seven_content in seven_contents:
                    if not isinstance(seven_content, dict):
                        continue
                    raw = seven_content.get("8", "")
                    if raw and "9" in seven_content:
                        raw = self._convert_text_attribute(raw, seven_content["9"])
                    text += raw

            elif text_type == "li" and two_five_contents:
                source_text = self._get_common_text(one_five_content)
                four_contents = one_five_content.get("4", {})
                hf = four_contents.get("hf", "")
                text = f"[{source_text}]({hf})" if hf else source_text
            else:
                text = ""
            if text:
                all_text += text
        return all_text

    def convert_h_func(self, content) -> str:
        """标题"""
        four = content.get("4", {})
        type_name = four.get("l", "h1")
        text = self._get_common_text(content)
        if text and type_name:
            level_str = type_name.replace("h", "")
            level = int(level_str) if level_str.isdigit() else 1
            text = " ".join(["#" * level, text])
        return text

    def convert_im_func(self, content):
        """图片"""
        four = content.get("4", {})
        image_url = four.get("u", "")
        return f"![]({image_url})"

    def convert_a_func(self, content):
        """附件"""
        four = content.get("4", {})
        fn = four.get("fn", "")
        fl = four.get("re", "")
        return f"[{fn}]({fl})"

    def convert_cd_func(self, content):
        """代码块"""
        four = content.get("4", {})
        language = four.get("la", "")
        codes = content.get("5", [])
        code_block = ""
        for code in codes:
            if isinstance(code, dict):
                code_block += self._get_common_text(code) + "\n"
        return f"```{language}\r\n{code_block}```"

    def convert_la_func(self, content):
        """高亮块"""
        lines = content.get("5", [])
        highlight_block = ""
        for line in lines:
            if isinstance(line, dict):
                highlight_block += self._get_common_text(line) + "\n"
        return f"```\r\n{highlight_block}```"

    def convert_q_func(self, content):
        """引用"""
        q_text_list = content.get("5", [])
        text = ""
        for q_text_dict in q_text_list:
            if isinstance(q_text_dict, dict):
                q_text = self._get_common_text(q_text_dict).replace("\n", "")
                text += f"> {q_text}\n"
        return text

    def convert_l_func(self, content):
        """有序列表和无序列表"""
        four = content.get("4", {})
        text = self._get_common_text(content)
        is_ordered = four.get("lt")
        if is_ordered == "unordered":
            level = four.get("ll", 1)
            return "\t" * (level - 1) + f"- {text}"
        elif is_ordered == "ordered":
            return f"1. {text}"
        return f"- {text}"

    def convert_t_func(self, content):
        """
        表格转换，生成符合测试期望的 Markdown 表格
        """
        nl = "\r\n"
        tr_list = content.get("5", [])
        if not tr_list:
            return ""

        rows = []
        max_cols = 0
        for tr in tr_list:
            cells = tr.get("5", [])
            row_cells = []
            for cell in cells:
                text = self._get_common_text(cell).strip()
                if not text:
                    text = " "
                row_cells.append(text)
            rows.append(row_cells)
            if len(row_cells) > max_cols:
                max_cols = len(row_cells)

        if max_cols == 0:
            return ""

        for row in rows:
            while len(row) < max_cols:
                row.append(" ")

        header = rows[0]
        separator = ["--"] * max_cols

        table_lines = ""
        # 表头行：末尾加空格
        table_lines += "| " + " | ".join(header) + " | " + nl
        # 分隔行：末尾不加空格
        table_lines += "| " + " | ".join(separator) + " |" + nl
        # 数据行：末尾加空格
        for row in rows[1:]:
            table_lines += "| " + " | ".join(row) + " | " + nl

        return table_lines

class YoudaoNoteConvert(object):
    """
    有道云笔记 note 内容转换为 markdown 内容
    """

    @staticmethod
    def covert_html_to_markdown(file_path):
        """
        转换 HTML 为 MarkDown
        :param file_path:
        :return:
        """
        with open(file_path, "rb") as f:
            content_str = f.read().decode("utf-8")
        from markdownify import markdownify as md

        # 如果换行符丢失，使用 md(content_str.replace('<br>', '<br><br>').replace('</div>', '</div><br><br>')).rstrip()
        new_content = md(content_str)
        base = os.path.splitext(file_path)[0]
        new_file_path = "".join([base, MARKDOWN_SUFFIX])
        os.rename(file_path, new_file_path)
        with open(new_file_path, "wb") as f:
            f.write(new_content.encode())

    @staticmethod
    def _covert_xml_to_markdown_content(file_path):
        # 使用 xml.etree.ElementTree 将 xml 文件转换为对象
        element_tree = ET.parse(file_path)
        note_element = element_tree.getroot()  # note Element

        # list_item 的 id 与 type 的对应
        list_item = {}
        for child in note_element[0]:
            if "list" in child.tag:
                list_item[child.attrib["id"]] = child.attrib["type"]

        body_element = note_element[1]  # Element
        new_content_list = []
        for element in list(body_element):
            text = XmlElementConvert.get_text_by_key(list(element))
            name = element.tag.replace("{http://note.youdao.com}", "").replace("-", "_")
            convert_func = getattr(
                XmlElementConvert, "convert_{}_func".format(name), None
            )
            # 如果没有转换，只保留文字
            if not convert_func:
                new_content_list.append(text)
                continue
            line_content = convert_func(text=text, element=element, list_item=list_item)
            new_content_list.append(line_content)
        return f"\r\n\r\n".join(new_content_list)  # 换行 1 行

    @staticmethod
    def covert_xml_to_markdown(file_path) -> bool:
        """
        转换 XML 为 MarkDown
        :param file_path:
        :return:
        """
        base = os.path.splitext(file_path)[0]
        new_file_path = "".join([base, MARKDOWN_SUFFIX])
        # 如果文件为空，结束
        if os.path.getsize(file_path) == 0:
            os.rename(file_path, new_file_path)
            return False

        new_content = YoudaoNoteConvert._covert_xml_to_markdown_content(file_path)
        os.rename(file_path, new_file_path)
        with open(new_file_path, "wb") as f:
            f.write(new_content.encode("utf-8"))
        return True

    @staticmethod
    def _covert_json_to_markdown_content(file_path):
        new_content_list = []
        with open(file_path, "r", encoding="utf-8") as f:
            try:
                json_data = json.load(f)
            except Exception as e:
                logging.error(e)
                json_data = {}

        json_contents = json_data["5"]
        for content in json_contents:
            type = content.get("6")
            if type:
                convert_func = getattr(
                    JsonConvert(), "convert_{}_func".format(type), None
                )
                if not convert_func:
                    line_content = JsonConvert().convert_text_func(content)
                else:
                    line_content = convert_func(content)
            else:
                # 无类型节点：检测是否为代码块容器
                children = content.get("5", [])
                has_lang = content.get("4", {}).get("la") is not None
                if has_lang or (children and all(child.get("6") == "cl" for child in children)):
                    line_content = JsonConvert().convert_cd_func(content)
                else:
                    line_content = JsonConvert().convert_text_func(content)

            if line_content:
                new_content_list.append(line_content)
        return f"\r\n\r\n".join(new_content_list)

    @staticmethod
    def covert_json_to_markdown(file_path) -> str:
        base = os.path.splitext(file_path)[0]
        new_file_path = "".join([base, MARKDOWN_SUFFIX])
        if os.path.getsize(file_path) == 0:
            os.rename(file_path, new_file_path)
            return new_file_path

        try:
            new_content = YoudaoNoteConvert._covert_json_to_markdown_content(file_path)
        except Exception as e:
            logging.error("JSON转换失败: %s", repr(e))
            # 不删除原始文件，返回空路径表示失败
            return ""

        with open(new_file_path, "wb") as f:
            f.write(new_content.encode("utf-8"))
        if os.path.exists(file_path):
            os.remove(file_path)
        return new_file_path