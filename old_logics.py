"""

def run_logic_sigma(self, alert):
    try:
        UULTF = self.state["conditions"]["UULTF"]["value"]
        ULTF = self.state["conditions"]["ULTF"]["value"]
        LTF = self.state["conditions"]["LTF"]["value"]
        MTF = self.state["conditions"]["MTF"]["value"]
        HTF = self.state["conditions"]["HTF"]["value"]
        UHTF = self.state["conditions"]["UHTF"]["value"]
    except KeyError:
        print(
            f"Incomplete dataset for user {self.user} {self.strat}, skipping decision"
        )
        return "Incomplete dataset, skipping decision"

    _trade_status = trade_status(self.py3c, self.state)  # long, short, idle

    if (
            UULTF == "buy"
            and ULTF == "buy"
            and LTF == "buy"
            and MTF == "buy"
            and HTF == "buy"
            and UHTF == "buy"
    ):
        if not _trade_status == "long":
            print(f"Opening {self.user} {self.strat} long.  Reason: all 6 TFs buy")
            trade_id = open_trade(
                self.py3c,
                account_id=self.account_id,
                pair=self.pair,
                _type="buy",
                leverage=self.leverage,
                units=self.units,
                tp_pct=self.tp_pct,
                tp_trail=self.tp_trail,
                sl_pct=self.sl_pct,
            )
            self.coll.update_one(
                {"_id": self.user},
                {"$set": {f"{self.strat}.status.trade_id": trade_id}},
                upsert=True,
            )
            return
    else:
        if _trade_status == "long":
            print(f"Closing {self.user} {self.strat} long")
            trade_id = self.state["status"]["trade_id"]
            close_trade(self.py3c, trade_id)
            return
    if DEBUG:
        print(
            f"Stars misaligned for {self.user} {self.strat} long, or already in trade, nothing to do"
        )

    if (
            UULTF == "sell"
            and ULTF == "sell"
            and LTF == "sell"
            and MTF == "sell"
            and HTF == "sell"
            and UHTF == "sell"
    ):
        if not _trade_status == "short":
            print(
                f"Opening {self.user} {self.strat} short.  Reason: all 6 TFs sell"
            )
            trade_id = open_trade(
                self.py3c,
                account_id=self.account_id,
                pair=self.pair,
                _type="sell",
                leverage=self.leverage,
                units=self.units,
                tp_pct=self.tp_pct,
                tp_trail=self.tp_trail,
                sl_pct=self.sl_pct,
            )
            self.coll.update_one(
                {"_id": self.user},
                {"$set": {f"{self.strat}.status.trade_id": trade_id}},
                upsert=True,
            )
            return
    else:
        if _trade_status == "short":
            print(f"Closing {self.user} {self.strat} short")
            trade_id = self.state["status"]["trade_id"]
            close_trade(self.py3c, trade_id)
            return
    if DEBUG:
        print(
            f"Stars misaligned for {self.user} {self.strat} short, or already in trade, nothing to do"
        )

   def run_logic_gamma(self, alert):
        self.state = self.coll.find_one({"_id": "indicators"})["SuperTrend"][self.coin]

        try:
            UULTF = self.state["conditions"]["1m"]
            ULTF = self.state["conditions"]["3m"]
            LTF = self.state["conditions"]["5m"]
            MTF = self.state["conditions"]["15m"]
            HTF = self.state["conditions"]["1h"]
            UHTF = self.state["conditions"]["4h"]
        except KeyError:
            print(
                f"{self.user} {self.strat }Incomplete dataset, skipping decision"
            )
            return "Incomplete dataset, skipping decision"

        _trade_status = trade_status(self.py3c, self.state)  # long, short, idle

        if (
            UULTF == "buy"
            and ULTF == "buy"
            and LTF == "buy"
            and MTF == "buy"
            and HTF == "buy"
            and UHTF == "buy"
        ):
            if not _trade_status == "long":
                print(f"Opening {self.user} {self.strat} long.  Reason: all 6 TFs buy")
                trade_id = open_trade(
                    self.py3c, account_id=self.account_id, pair=self.pair, _type="buy"
                )
                self.coll.update_one(
                    {"_id": self.user},
                    {"$set": {f"{self.strat}.status.trade_id": trade_id}},
                )
                return
        elif _trade_status == "long":
            print(f"Closing {self.user} {self.strat} long")
            trade_id = self.state["status"]["trade_id"]
            close_trade(self.py3c, trade_id)
            return
        if DEBUG:
            print(
                f"Stars misaligned for {self.user} {self.strat} long, or already in trade, nothing to do"
            )

        if (
            UULTF == "sell"
            and ULTF == "sell"
            and LTF == "sell"
            and MTF == "sell"
            and HTF == "sell"
            and UHTF == "sell"
        ):
            if not _trade_status == "short":
                print(
                    f"Opening {self.user} {self.strat} short.  Reason: all 6 TFs sell"
                )
                trade_id = open_trade(
                    self.py3c, account_id=self.account_id, pair=self.pair, _type="sell"
                )
                self.coll.update_one(
                    {"_id": self.user},
                    {"$set": {f"{self.strat}.status.trade_id": trade_id}},
                    upsert=True,
                )
                return
        else:
            if _trade_status == "short":
                print(f"Closing {self.user} {self.strat} short")
                trade_id = self.state["status"]["trade_id"]
                close_trade(self.py3c, trade_id)
                return
        if DEBUG:
            print(
                f"Stars misaligned for {self.user} {self.strat} short, or already in trade, nothing to do"
            )

"""