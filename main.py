import tensorflow as tf
from tensorflow.keras.models import load_model # type: ignore
import numpy as np
#from tensorflow.keras.layers import TFSMLayer
from fastapi import FastAPI, Request, HTTPException
from fastapi import Query
from fastapi.templating import Jinja2Templates
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse
from typing import List
from sql import save_to_db, select_for_db, update_fraud, get_fraud_statistics
from pydantic import BaseModel
import csv
import pandas as pd

app = FastAPI()
templates = Jinja2Templates(directory="templates")

loaded_model = load_model('../Sequential_model')

class AntifraudData(BaseModel):
    user_id: int
    distance_from_home: float
    distance_from_last_transaction: float
    ratio_to_median_purchase_price: float
    repeat_retailer: float
    used_chip: float
    used_pin_number: float
    online_order: float

class ChangeAntifraudData(BaseModel):
    user_id: int
    fraud: str
    transaction_id: int

class UserIdsRequest(BaseModel):
    user_ids: List[int]




def getantifraud(antifraud_data: AntifraudData):
    value_list = [antifraud_data.distance_from_home,
                  antifraud_data.distance_from_last_transaction,
                  antifraud_data.ratio_to_median_purchase_price,
                  antifraud_data.repeat_retailer,
                  antifraud_data.used_chip,
                  antifraud_data.used_pin_number,
                  antifraud_data.online_order]
    
    array_data = np.array([value_list])
    return array_data



@app.post("/getantifraud")
async def antifraud_handler(antifraud_data: AntifraudData):
    predictions = loaded_model.predict(getantifraud(antifraud_data))
    results = []
    for prediction in predictions:
        prediction = float(prediction)
        if prediction > 0.5:
            fraud_tb = 'FRAUD'
        elif 0.2 < prediction < 0.5:
            fraud_tb = 'NEED ANALYTICS'
        else:
            fraud_tb = 'NOT FRAUD'
        # Сохранение данных в базу
        await save_to_db(
            antifraud_data.user_id, 
            antifraud_data.distance_from_home, 
            antifraud_data.distance_from_last_transaction, 
            antifraud_data.ratio_to_median_purchase_price, 
            antifraud_data.repeat_retailer, 
            antifraud_data.used_chip, 
            antifraud_data.used_pin_number, 
            antifraud_data.online_order, 
            fraud_tb
        )
        results.append({
            "prediction": prediction,
            "fraud_status": fraud_tb
        })
    return {"results": results}
    

@app.get("/allvalues")
async def show_table(request: Request, 
                     user_id: int = Query(None),
                     fraud: str = Query(None)):
    transactions_data = await select_for_db(user_id=user_id, fraud=fraud)
    return templates.TemplateResponse("table.html", {"request": request, "transactions_data": transactions_data})

@app.get("/export")
async def export_data(user_id: int = Query(None),
                      fraud: str = Query(None)):
    data = await select_for_db(user_id=user_id, fraud=fraud)
    
    df = pd.DataFrame(data, columns=["transaction_id", "user_id", "distance_from_home", "distance_from_last_transaction", "ratio_to_median_purchase_price", "repeat_retailer", "used_chip", "used_pin_number", "online_order", "fraud"])

    output_file = 'output.xlsx'
    df.to_excel(output_file, index=False)

    return FileResponse(output_file, filename='output.xlsx', media_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')

@app.get("/needanalytics", response_class=HTMLResponse)
async def read_transactions(request: Request):
    transactions_data = await select_for_db(fraud="NEED ANALYTICS")
    return templates.TemplateResponse("table_button.html", {"request": request, "transactions_data": transactions_data})

@app.post("/update_fraud")
async def update_fraud_post(change_data: ChangeAntifraudData):
    return await update_fraud(change_data.fraud,change_data.user_id,change_data.transaction_id)

@app.get("/diagram")
async def get_diagram(request: Request):
    fraud_fraud_count, fraud_not_fraud_count = await get_fraud_statistics()
    total_count = fraud_fraud_count + fraud_not_fraud_count
    if total_count > 0:
        fraud_fraud_percentage = (fraud_fraud_count / total_count) * 100
        fraud_not_fraud_percentage = (fraud_not_fraud_count / total_count) * 100
    else:
        fraud_fraud_percentage = 0
        fraud_not_fraud_percentage = 0
    return templates.TemplateResponse("diagram.html", {
        "request": request,
        "fraud_fraud_percentage": fraud_fraud_percentage,
        "fraud_fraud_count": fraud_fraud_count,
        "fraud_not_fraud_percentage": fraud_not_fraud_percentage,
        "fraud_not_fraud_count": fraud_not_fraud_count
    })

@app.get("/payment_form")
async def payment_form(request: Request):
    data = {"message": "payment_form"}
    return templates.TemplateResponse("payment_form.html", {"request": request, "data": data})

@app.get("/get_data_by_user_id")
async def get_data_by_user_id(request: Request, 
                     user_id: int = Query(None)):
    try:
        request_data = await request.json()
        user_ids_request = UserIdsRequest(**request_data)
    except Exception as e:
        raise HTTPException(status_code=400, detail="Invalid JSON input")
    
    all_data = []
    for user_id in user_ids_request.user_ids:
        data = await select_for_db(user_id=user_id)
        all_data.extend(data)
    
    if not all_data:
        raise HTTPException(status_code=404, detail="Data not found for the given user_ids")
    response = []
    for row in all_data:
        response.append({
            "transaction_id": row[0],
            "user_id": row[1],
            "distance_from_home": row[2],
            "distance_from_last_transaction": row[3],
            "ratio_to_median_purchase_price": row[4],
            "repeat_retailer": row[5],
            "used_chip": row[6],
            "used_pin_number": row[7],
            "online_order": row[8],
            "fraud": row[9]
        })
    
    return {"data": response}