import aiosqlite
from fastapi.responses import HTMLResponse, JSONResponse



#создает запись в бд
async def save_to_db(user_id, distance_from_home, distance_from_last_transaction, ratio_to_median_purchase_price, repeat_retailer, used_chip, used_pin_number, online_order, fraud):
    async with aiosqlite.connect('../db/antifraud_service.db') as db:
        await db.execute('INSERT INTO transactions_data (user_id, distance_from_home, distance_from_last_transaction, ratio_to_median_purchase_price, repeat_retailer, used_chip, used_pin_number, online_order, fraud) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)', 
                        (user_id, distance_from_home, distance_from_last_transaction, ratio_to_median_purchase_price, repeat_retailer, used_chip, used_pin_number, online_order, fraud))
        await db.commit()

#выгрузка данных из бд
async def select_for_db(user_id: int = None, fraud: str = None):
    query = "SELECT * FROM transactions_data WHERE 1=1"
    params = []
    if user_id is not None:
        query += " AND user_id = ?"
        params.append(user_id)
    if fraud is not None:
        query += " AND fraud = ?"
        params.append(fraud)
    async with aiosqlite.connect('../db/antifraud_service.db') as db:
        cursor = await db.cursor()
        await cursor.execute(query, params)
        select_result = await cursor.fetchall()
        return select_result

#обновление данных фрод/не фрод
async def update_fraud(fraud,user_id,transaction_id):
    async with aiosqlite.connect('../db/antifraud_service.db') as db:
        cursor = await db.cursor()
        await cursor.execute('UPDATE transactions_data SET fraud = ? WHERE  user_id = ? and transaction_id = ?', (fraud,user_id,transaction_id))
        await db.commit()
        return JSONResponse(content={"message": "Значение изменено"})

async def get_fraud_statistics():
    async with aiosqlite.connect('../db/antifraud_service.db') as db:
        cursor = await db.cursor()
        await cursor.execute("SELECT COUNT(*) FROM transactions_data WHERE fraud = 'FRAUD'")
        fraud_fraud_count = (await cursor.fetchone())[0]
        await cursor.execute("SELECT COUNT(*) FROM transactions_data WHERE fraud = 'NOT FRAUD'")
        fraud_not_fraud_count = (await cursor.fetchone())[0]
    return fraud_fraud_count, fraud_not_fraud_count