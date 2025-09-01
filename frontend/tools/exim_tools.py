"""
title: Exim Tools
version: 0.0.1
author: ppoak
author_url: https://github.com/ppoak
description: A series of tools for your job at Exim (China Export-Import Bank)
"""

import re
import os
import pandas as pd


class Tools:
    def financial_report_analyze(self, path: str):
        """当用户需要进行财务报告分析并给定一个财务报告路径时，你可以使用该工具，传入该路径，即可获取财务分析结果表格。
        :param path: 财务报告路径
        :return: 财务报告表格
        """
        parser = ReportParser(path)
        table = parser()
        table_markdown = table.to_markdown()
        return table_markdown    


class ReportParser:
    def __init__(self, path: str):
        self.path = path
        files = os.listdir(self.path)
        report_dict = {}
        annual_report_pat = re.compile(r"([12]\d{3})年报")
        quarterly_report_pat = re.compile(r"([12]\d{3})([一二三四])季报")
        for f in files:
            year_match = annual_report_pat.search(f)
            quarter_match = quarterly_report_pat.search(f)
            if year_match:
                y = int(year_match.group(1))
                report_dict[("annual", y)] = os.path.join(path, f)
            elif quarter_match:
                y = int(quarter_match.group(1))
                q = quarter_match.group(2) + "季度"
                report_dict[("quarter", y, q)] = os.path.join(path, f)
        self.report_dict = report_dict

    def select_reports(self):
        year_list = sorted([k[1] for k in self.report_dict if k[0] == "annual"])
        last_3_years = year_list[-3:]
        selected = {
            ("annual", year): self.report_dict[("annual", year)]
            for year in last_3_years
        }
        quarter_candidates = [k for k in self.report_dict if k[0] == "quarter"]
        if quarter_candidates:
            quarters_sorted = sorted(
                quarter_candidates, key=lambda t: (t[1], t[2]), reverse=True
            )
            newest = quarters_sorted[0]
            selected[newest] = self.report_dict[newest]
            last_year_same = ("quarter", newest[1] - 1, newest[2])
            if last_year_same in self.report_dict:
                selected[last_year_same] = self.report_dict[last_year_same]
        return selected

    def load_reports(self, selected_files):
        data = {}
        for k, path in selected_files.items():
            sheets = {}
            for sheet in ["资产负债表", "利润表", "现金流量表"]:
                df = pd.read_excel(path, sheet_name=sheet)
                df = df.set_index(df.columns[0]).squeeze()
                sheets[sheet] = df
            data[k] = sheets
        return data

    def get_account(self, df, account, default=None):
        subject_map = {
            "总资产": "资产总计",
            "净资产": "所有者权益（或股东权益）合计",
            "长期借款": "长期借款",
            "短期借款": "短期借款",
            "一年内到期的长期借款": "一年内到期的非流动负债",
            "应付票据": "应付票据",
            "负债合计": "负债合计",
            "流动资产合计": "流动资产合计",
            "流动负债合计": "流动负债合计",
            "存货": "存货",
            "应收账款": "应收账款",
            "其他应收款": "其他应收款",
            "营业收入": "营业收入",
            "营业成本": "营业成本",
            "营业利润": "营业利润",
            "利润总额": "利润总额",
            "净利润": "净利润",
            "经营活动现金净流量": "经营活动产生的现金流量净额",
            "投资活动现金净流量": "投资活动产生的现金流量净额",
            "筹资活动现金净流量": "筹资活动产生的现金流量净额",
            "净现金流": "现金及现金等价物净增加额",
            "经营活动现金流入": "经营活动现金流入小计",
        }
        return df.get(subject_map.get(account, account), default) / 1e8

    def get_initial_balance(self, data, key):
        if key[0] == "annual":
            prev_key = ("annual", key[1] - 1)
        elif key[0] == "quarter":
            prev_key = ("annual", key[1] - 1)
        else:
            return None
        if prev_key in data:
            prev_sheet = data[prev_key]["资产负债表"]
            return {
                subj: self.get_account(prev_sheet, subj)
                for subj in ["应收账款", "存货", "流动资产合计"]
            }
        else:
            return {subj: None for subj in ["应收账款", "存货", "流动资产合计"]}

    def calc_indicators(self, data, report_keys):
        debt_accounts = ["短期借款", "长期借款", "一年内到期的长期借款"]
        table = []
        # 输出字段（中文）：用于最终表头
        columns_zh = [
            "总资产",
            "净资产",
            "长期借款",
            "短期借款",
            "一年内到期的长期借款",
            "应付票据",
            "资产负债率",
            "流动比率",
            "速动比率",
            "带息负债比率",
            "应收账款",
            "其他应收款",
            "存货",
            "应收账款周转率",
            "存货周转次率",
            "流动资产周转率",
            "两金占流动资产比重",
            "营业收入",
            "营业利润",
            "利润总额",
            "净利润",
            "销售利润率",
            "净资产收益率",
            "经营活动现金净流量",
            "投资活动现金净流量",
            "筹资活动现金净流量",
            "净现金流",
            "经营活动现金流入",
            "经营活动现金流入/营业收入",
            "盈余现金保障倍数",
        ]
        for key in report_keys:
            bal, inc, cash = (
                data[key]["资产负债表"],
                data[key]["利润表"],
                data[key]["现金流量表"],
            )
            init_dict = self.get_initial_balance(data, key)
            row = {}
            # 以下均为中文指标名
            row["总资产"] = self.get_account(bal, "总资产")
            row["净资产"] = self.get_account(bal, "净资产")
            row["长期借款"] = self.get_account(bal, "长期借款")
            row["短期借款"] = self.get_account(bal, "短期借款")
            row["一年内到期的长期借款"] = self.get_account(bal, "一年内到期的长期借款")
            row["应付票据"] = self.get_account(bal, "应付票据")
            total_assets = row["总资产"]
            total_liabilities = self.get_account(bal, "负债合计")
            row["资产负债率"] = (
                f"{(total_liabilities / total_assets * 100):.2f}%"
                if total_assets and total_liabilities
                else None
            )
            current_assets_end = self.get_account(bal, "流动资产合计")
            current_liabilities = self.get_account(bal, "流动负债合计")
            row["流动比率"] = (
                current_assets_end / current_liabilities
                if current_liabilities
                else None
            )
            inventory_end = self.get_account(bal, "存货")
            row["速动比率"] = (
                (current_assets_end - inventory_end) / current_liabilities
                if current_assets_end and inventory_end and current_liabilities
                else None
            )
            interest_debt = sum([(self.get_account(bal, k, 0)) for k in debt_accounts])
            row["带息负债比率"] = (
                f"{(interest_debt / total_assets * 100):.2f}%" if total_assets else None
            )
            row["应收账款"] = self.get_account(bal, "应收账款")
            row["其他应收款"] = self.get_account(bal, "其他应收款")
            row["存货"] = inventory_end
            revenue = self.get_account(inc, "营业收入")
            ar_open = init_dict["应收账款"] or row["应收账款"]
            ar_end = row["应收账款"]
            if ar_open and ar_end and revenue:
                row["应收账款周转率"] = round(revenue / ((ar_open + ar_end) / 2), 2)
            else:
                row["应收账款周转率"] = None
            op_cost = (
                self.get_account(inc, "营业成本")
                if self.get_account(inc, "营业成本")
                else None
            )
            inv_open = init_dict["存货"] or inventory_end
            if op_cost and inv_open and inventory_end:
                row["存货周转次率"] = round(
                    op_cost / ((inv_open + inventory_end) / 2), 2
                )
            else:
                row["存货周转次率"] = None
            curr_ast_open = init_dict["流动资产合计"] or current_assets_end
            if revenue and curr_ast_open and current_assets_end:
                row["流动资产周转率"] = round(
                    revenue / ((curr_ast_open + current_assets_end) / 2), 2
                )
            else:
                row["流动资产周转率"] = None
            two_assets = (row["应收账款"] if row["应收账款"] else 0) + (
                row["其他应收款"] if row["其他应收款"] else 0
            )
            row["两金占流动资产比重"] = (
                f"{(two_assets / current_assets_end * 100):.2f}%"
                if current_assets_end
                else None
            )
            row["营业收入"] = revenue
            row["营业利润"] = self.get_account(inc, "营业利润")
            row["利润总额"] = self.get_account(inc, "利润总额")
            row["净利润"] = self.get_account(inc, "净利润")
            row["销售利润率"] = (
                f"{(row['净利润'] / revenue * 100):.2f}%"
                if revenue and row["净利润"]
                else None
            )
            row["净资产收益率"] = (
                f"{(row['净利润'] / row['净资产'] * 100):.2f}%"
                if row["净资产"] and row["净利润"]
                else None
            )
            row["经营活动现金净流量"] = self.get_account(cash, "经营活动现金净流量")
            row["投资活动现金净流量"] = self.get_account(cash, "投资活动现金净流量")
            row["筹资活动现金净流量"] = self.get_account(cash, "筹资活动现金净流量")
            row["净现金流"] = self.get_account(cash, "净现金流")
            row["经营活动现金流入"] = self.get_account(cash, "经营活动现金流入")
            row["经营活动现金流入/营业收入"] = (
                round(row["经营活动现金流入"] / revenue, 2)
                if revenue and row["经营活动现金流入"]
                else None
            )
            row["盈余现金保障倍数"] = (
                round(row["经营活动现金净流量"] / row["净利润"], 2)
                if row["净利润"] and row["经营活动现金净流量"]
                else None
            )
            if key[0] == "annual":
                report_name = f"{key[1]}年"
            else:
                report_name = f"{key[1]}年{key[2]}"
            # 保证每列都是中文且顺序
            table.append((report_name, [row.get(col) for col in columns_zh]))
        # 用 DataFrame 的 index 指定为 columns_zh，
        return pd.DataFrame(dict(table), index=columns_zh)

    def __call__(self):
        selected_files = self.select_reports()
        data = self.load_reports(selected_files)
        indicators_df = self.calc_indicators(data, list(selected_files.keys()))
        return indicators_df
