from flask_restful import Resource, reqparse
from models.tickers import TickerModel
from flask_jwt_extended import jwt_required, get_jwt
from models.pairs import PairModel
from models.signals import SignalModel

EMPTY_ERR = "'{}' cannot be empty!"
NAME_ERR = "'{}' with that name already exists."
INSERT_ERR = "an error occurred inserting the item."
UPDATE_ERR = "an error occurred updating the item."
DELETE_ERR = "an error occurred deleting the item."
GET_ERR = "an error occurred while getting the item(s)."
CREATE_OK = "'{}' created successfully."
DELETE_OK = "'{}' deleted successfully."
NOT_FOUND = "item not found."
PRIV_ERR = "'{}' privilege required."
TICKR_ERR = " ticker is already active in a pair!"
PASS_ERR = "incorrect passphrase."


class TickerUpdatePNL(Resource):
    parser = reqparse.RequestParser()
    parser.add_argument(
        "passphrase", type=str, required=True, help=EMPTY_ERR.format("passphrase")
    )
    parser.add_argument(
        "symbol", type=str, required=True, help=EMPTY_ERR.format("symbol")
    )
    parser.add_argument("active_pos", type=float)
    parser.add_argument("active_pnl", type=float)
    parser.add_argument("active_cost", type=float)

    @staticmethod  # this is to update PNL and no need to have an active session
    def put():
        data = TickerUpdatePNL.parser.parse_args()

        # format return message inline with flask_restful parser errors
        if SignalModel.passphrase_wrong(data["passphrase"]):
            return_msg = {"message": {"passphrase": PASS_ERR}}
            #  return {"message": PASS_ERR}, 400  # return Bad Request
            return return_msg, 400  # return Bad Request

        # get ticker with symbol
        item = TickerModel.find_by_symbol(data["symbol"])

        if item:

            item.active_pos = data["active_pos"]
            item.active_pnl = data["active_pnl"]
            item.active_cost = data["active_cost"]

            try:
                item.update(1)

            except Exception as e:
                print("Error occurred - ", e)
                return (
                    {"message": UPDATE_ERR},
                    500,
                )  # Return Interval Server Error

            return item.json()

        return {"message": NOT_FOUND}, 404  # Return Not Found


class TickerRegister(Resource):
    parser = reqparse.RequestParser()
    parser.add_argument(
        "symbol", type=str, required=True, help=EMPTY_ERR.format("symbol")
    )
    parser.add_argument("sectype", type=str, default="STK")
    parser.add_argument("xch", type=str, default="SMART")
    parser.add_argument("prixch", type=str, default="NYSE")
    parser.add_argument("currency", type=str, default="USD")
    parser.add_argument("order_type", type=str, default="RELATIVE")
    parser.add_argument("active", type=int, default=0)
    # update_pnl to be "True" to update active_pos, active_pnl, active_cost
    parser.add_argument("update_pnl", type=bool, default=False)
    parser.add_argument("active_pos", type=float, default=0)
    parser.add_argument("active_pnl", type=float, default=0)
    parser.add_argument("active_cost", type=float, default=0)

    @staticmethod
    @jwt_required(fresh=True)  # need fresh token
    def post():
        data = TickerRegister.parser.parse_args()

        if TickerModel.find_by_symbol(data["symbol"]):
            return (
                {"message": NAME_ERR.format("ticker")},
                400,
            )  # Return Bad Request

        item = TickerModel(
            data["symbol"],
            data["sectype"],
            data["xch"],
            data["prixch"],
            data["currency"],
            data["order_type"],
            data["active"],
            data["active_pos"],
            data["active_pnl"],
            data["active_cost"],
        )

        if item.active == 1:

            if PairModel.find_active_ticker(item.symbol):
                return (
                    {"message": TICKR_ERR},
                    400,
                )  # Return Bad Request

        try:
            item.insert()

        except Exception as e:
            print("Error occurred - ", e)  # better log the errors
            return (
                {"message": INSERT_ERR},
                500,
            )  # Return Interval Server Error

        return (
            {"message": CREATE_OK.format("ticker")},
            201,
        )  # Return Successful Creation of Resource

    @staticmethod
    @jwt_required(fresh=True)  # need fresh token
    def put():
        data = TickerRegister.parser.parse_args()

        item = TickerModel(
            data["symbol"],
            data["sectype"],
            data["xch"],
            data["prixch"],
            data["currency"],
            data["order_type"],
            data["active"],
            data["active_pos"],
            data["active_pnl"],
            data["active_cost"],
        )

        if item.active == 1:

            if PairModel.find_active_ticker(item.symbol):
                return (
                    {"message": TICKR_ERR},
                    400,
                )  # Return Bad Request

        item_to_update = TickerModel.find_by_symbol(data["symbol"])

        if item_to_update:
            try:
                print(data["update_pnl"])
                item.update(data["update_pnl"])

            except Exception as e:
                print("Error occurred - ", e)
                return (
                    {"message": UPDATE_ERR},
                    500,
                )  # Return Interval Server Error

            return item_to_update.json()

        try:
            item.insert()

        except Exception as e:
            print("Error occurred - ", e)
            return (
                {"message": INSERT_ERR},
                500,
            )  # Return Interval Server Error

        return (
            {"message": CREATE_OK.format("ticker")},
            201,
        )  # Return Successful Creation of Resource


class TickerList(Resource):
    @staticmethod
    def get(number_of_items="0"):
        try:
            items = TickerModel.get_rows(number_of_items)

        except Exception as e:
            print("Error occurred - ", e)
            return (
                {"message": GET_ERR},
                500,
            )  # Return Interval Server Error

        # return {'tickers': list(map(lambda x: x.json(), items))}  # we can map the list of objects,
        return {
            "tickers": [item.json() for item in items]
        }  # but this one is slightly more readable


class Ticker(Resource):
    @staticmethod
    def get(symbol):

        try:
            item = TickerModel.find_by_symbol(symbol)

        except Exception as e:
            print("Error occurred - ", e)
            return (
                {"message": GET_ERR},
                500,
            )  # Return Interval Server Error

        if item:
            return item.json()

        return {"message": NOT_FOUND}, 404  # Return Not Found

    @staticmethod
    @jwt_required(fresh=True)  # need fresh token
    def delete(symbol):

        claims = get_jwt()

        # TODO: consider user to delete own data
        if not claims["is_admin"]:
            return {"message": PRIV_ERR.format("admin")}, 401  # Return Unauthorized

        try:
            item_to_delete = TickerModel.find_by_symbol(symbol)

            if item_to_delete:
                item_to_delete.delete()
            else:
                return {"message": NOT_FOUND}

        except Exception as e:
            print("Error occurred - ", e)
            return (
                {"message": DELETE_ERR},
                500,
            )  # Return Interval Server Error

        return {"message": DELETE_OK.format("ticker")}
