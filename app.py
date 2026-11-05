from flask import Flask, jsonify, request, redirect, render_template
import config
import base64
from io import BytesIO

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

app = Flask(__name__)


# Home page
@app.route("/")
def home():
    return render_template("home.html")


# Show all weather records
@app.route("/weather", methods=["GET"])
def get_weather():
    db = config.connect()
    cursor = db.cursor(dictionary=True)

    try:
        cursor.execute("SELECT * FROM weather ORDER BY id")
        records = cursor.fetchall()

        for row in records:
            if row.get("weather_date"):
                row["weather_date"] = row["weather_date"].isoformat()

        return render_template("weather_data.html", records=records)

    finally:
        cursor.close()
        db.close()


# Search weather records by city
@app.route("/weather/city/<city>", methods=["GET"])
def get_city_weather(city):
    db = config.connect()
    cursor = db.cursor(dictionary=True)

    try:
        cursor.execute(
            "SELECT * FROM weather WHERE city LIKE %s ORDER BY id",
            ("%" + city + "%",)
        )
        records = cursor.fetchall()

        for row in records:
            if row.get("weather_date"):
                row["weather_date"] = row["weather_date"].isoformat()

        return render_template("weather_data.html", records=records)

    finally:
        cursor.close()
        db.close()


# Add weather data using JSON
@app.route("/weather", methods=["POST"])
def add_weather_json():
    data = request.get_json(silent=True)

    if not data:
        return jsonify({"error": "Please send JSON data"}), 400

    required = [
        "city", "temperature", "humidity",
        "rainfall", "wind_speed",
        "weather_condition", "weather_date"
    ]

    if any(key not in data for key in required):
        return jsonify({
            "error": "Please provide all required fields"
        }), 400

    db = config.connect()
    cursor = db.cursor()

    try:
        query = """
            INSERT INTO weather
            (city, temperature, humidity, rainfall,
             wind_speed, weather_condition, weather_date)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
        """

        values = (
            data["city"],
            data["temperature"],
            data["humidity"],
            data["rainfall"],
            data["wind_speed"],
            data["weather_condition"],
            data["weather_date"]
        )

        cursor.execute(query, values)
        db.commit()

        return jsonify({
            "message": "Weather record added successfully"
        }), 201

    except Exception as e:
        db.rollback()
        return jsonify({"error": str(e)}), 400

    finally:
        cursor.close()
        db.close()


# Average temperature by city
@app.route("/weather/analysis/average", methods=["GET"])
def average_temperature():
    db = config.connect()
    cursor = db.cursor(dictionary=True)

    try:
        cursor.execute("""
            SELECT city,
                   ROUND(AVG(temperature), 2) AS average_temperature
            FROM weather
            GROUP BY city
            ORDER BY city
        """)

        records = cursor.fetchall()

        return render_template(
            "average_temperature.html",
            records=records
        )

    finally:
        cursor.close()
        db.close()


# Open Add Data page
@app.route("/add_data", methods=["GET"])
def add_data_page():
    return render_template(
        "add_data.html",
        message=request.args.get("message", "")
    )


# Add data using HTML form
@app.route("/add", methods=["POST"])
def add_weather_form():
    db = config.connect()
    cursor = db.cursor()

    try:
        query = """
            INSERT INTO weather
            (city, temperature, humidity, rainfall,
             wind_speed, weather_condition, weather_date)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
        """

        values = (
            request.form["city"],
            float(request.form["temperature"]),
            int(request.form["humidity"]),
            float(request.form["rainfall"]),
            float(request.form["wind_speed"]),
            request.form["weather_condition"],
            request.form["weather_date"]
        )

        cursor.execute(query, values)
        db.commit()

    except Exception as e:
        db.rollback()
        return f"Could not add data: {e}", 400

    finally:
        cursor.close()
        db.close()

    return redirect("/add_data?message=Data+added+successfully")


# Open Update Data page
@app.route("/update_data", methods=["GET"])
def update_data_page():
    return render_template(
        "update_data.html",
        message=request.args.get("message", "")
    )


# Update existing weather data
@app.route("/update", methods=["POST"])
def update_weather():
    db = config.connect()
    cursor = db.cursor()

    try:
        record_id = int(request.form["id"])

        query = """
            UPDATE weather
            SET city = %s,
                temperature = %s,
                humidity = %s,
                rainfall = %s,
                wind_speed = %s,
                weather_condition = %s,
                weather_date = %s
            WHERE id = %s
        """

        values = (
            request.form["city"],
            float(request.form["temperature"]),
            int(request.form["humidity"]),
            float(request.form["rainfall"]),
            float(request.form["wind_speed"]),
            request.form["weather_condition"],
            request.form["weather_date"],
            record_id
        )

        cursor.execute(query, values)

        if cursor.rowcount == 0:
            cursor.execute(
                "SELECT id FROM weather WHERE id = %s",
                (record_id,)
            )

            if cursor.fetchone() is None:
                db.rollback()
                return "Record ID not found", 404

        db.commit()

    except Exception as e:
        db.rollback()
        return f"Could not update data: {e}", 400

    finally:
        cursor.close()
        db.close()

    return redirect("/update_data?message=Data+updated+successfully")


# Open Delete Data page
@app.route("/delete_data", methods=["GET"])
def delete_data_page():
    db = config.connect()
    cursor = db.cursor(dictionary=True)

    try:
        cursor.execute("SELECT * FROM weather ORDER BY id")
        records = cursor.fetchall()

        for row in records:
            if row.get("weather_date"):
                row["weather_date"] = row["weather_date"].isoformat()

        return render_template("delete_data.html", records=records)

    finally:
        cursor.close()
        db.close()


# Delete weather data using ID
@app.route("/delete/<int:id>", methods=["POST"])
def delete_weather(id):
    db = config.connect()
    cursor = db.cursor()

    try:
        cursor.execute("DELETE FROM weather WHERE id = %s", (id,))

        if cursor.rowcount == 0:
            db.rollback()
            return "Weather record not found", 404

        db.commit()
        return redirect("/delete_data")

    except Exception as e:
        db.rollback()
        return f"Could not delete data: {e}", 400

    finally:
        cursor.close()
        db.close()


# Weather analysis dashboard: five graphs
@app.route("/weather/analysis/graph", methods=["GET"])
def weather_graph():
    db = config.connect()
    cursor = db.cursor(dictionary=True)

    try:
        cursor.execute("""
            SELECT city, temperature, humidity, rainfall,
                   wind_speed, weather_condition
            FROM weather
            ORDER BY city
        """)

        records = cursor.fetchall()

        if not records:
            return "No weather data available. Add records first."

        # Get all cities
        cities = sorted(set(str(r["city"]) for r in records))

        # Average temperature by city
        avg_temperature = []

        for city in cities:
            values = [
                float(r["temperature"])
                for r in records
                if str(r["city"]) == city
                and r["temperature"] is not None
            ]

            avg_temperature.append(
                sum(values) / len(values) if values else 0
            )

        # Average humidity by city
        avg_humidity = []

        for city in cities:
            values = [
                float(r["humidity"])
                for r in records
                if str(r["city"]) == city
                and r["humidity"] is not None
            ]

            avg_humidity.append(
                sum(values) / len(values) if values else 0
            )

        # Total rainfall by city
        total_rainfall = []

        for city in cities:
            values = [
                float(r["rainfall"] or 0)
                for r in records
                if str(r["city"]) == city
            ]

            total_rainfall.append(sum(values))

        # Average wind speed by city
        avg_wind_speed = []

        for city in cities:
            values = [
                float(r["wind_speed"])
                for r in records
                if str(r["city"]) == city
                and r["wind_speed"] is not None
            ]

            avg_wind_speed.append(
                sum(values) / len(values) if values else 0
            )

        # Count weather conditions for each city
        conditions = {}

        for row in records:
            city = str(row["city"])
            condition = str(
                row["weather_condition"] or "Unknown"
            ).strip().title()

            key = (city, condition)
            conditions[key] = conditions.get(key, 0) + 1

        condition_names = sorted(
            set(condition for city, condition in conditions)
        )

        # Create a dashboard with five graphs
        fig, axes = plt.subplots(3, 2, figsize=(15, 16))

        # Graph 1: Average temperature
        axes[0, 0].bar(cities, avg_temperature)
        axes[0, 0].set_title("Average Temperature by City")
        axes[0, 0].set_ylabel("Temperature (°C)")
        axes[0, 0].tick_params(axis="x", rotation=30)

        # Graph 2: Average humidity
        axes[0, 1].bar(cities, avg_humidity)
        axes[0, 1].set_title("Average Humidity by City")
        axes[0, 1].set_ylabel("Humidity (%)")
        axes[0, 1].tick_params(axis="x", rotation=30)

        # Graph 3: Total rainfall
        axes[1, 0].bar(cities, total_rainfall)
        axes[1, 0].set_title("Total Rainfall by City")
        axes[1, 0].set_ylabel("Rainfall (recorded units)")
        axes[1, 0].tick_params(axis="x", rotation=30)

        # Graph 4: Average wind speed
        axes[1, 1].bar(cities, avg_wind_speed)
        axes[1, 1].set_title("Average Wind Speed by City")
        axes[1, 1].set_ylabel("Wind speed (recorded units)")
        axes[1, 1].tick_params(axis="x", rotation=30)

        # Graph 5: Weather conditions by city
        x_positions = list(range(len(cities)))
        bottom = [0] * len(cities)

        for condition in condition_names:
            counts = [
                conditions.get((city, condition), 0)
                for city in cities
            ]

            axes[2, 0].bar(
                x_positions,
                counts,
                bottom=bottom,
                label=condition
            )

            bottom = [
                bottom[i] + counts[i]
                for i in range(len(cities))
            ]

        axes[2, 0].set_title("Weather Conditions by City")
        axes[2, 0].set_ylabel("Number of records")
        axes[2, 0].set_xticks(x_positions)
        axes[2, 0].set_xticklabels(cities, rotation=30)
        axes[2, 0].legend(title="Condition")

        # Hide the unused sixth position
        axes[2, 1].axis("off")

        fig.tight_layout()

        # Convert graphs into an image for HTML
        buffer = BytesIO()
        fig.savefig(buffer, format="png", dpi=120)
        plt.close(fig)

        buffer.seek(0)

        graph_image = base64.b64encode(
            buffer.getvalue()
        ).decode("utf-8")

        return render_template(
            "weather_graph.html",
            graph_image=graph_image
        )

    finally:
        cursor.close()
        db.close()


if __name__ == "__main__":
    app.run(debug=True)