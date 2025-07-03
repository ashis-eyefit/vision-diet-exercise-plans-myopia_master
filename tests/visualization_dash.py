import dash
from dash import dcc, html, Input, Output
import plotly.graph_objs as go
import requests

app = dash.Dash(__name__)
app.title = "Fatigue Score Viewer"

# Set your FastAPI endpoint URL
FASTAPI_URL = "http://localhost:8000/fatigue-score-prediction"

# Dash layout
app.layout = html.Div([
    html.H2("📊 Fatigue Score Viewer", style={'textAlign': 'center'}),

    html.Div([
        html.Label("Enter User ID:"),
        dcc.Input(
            id='user-id-input',
            type='text',
            placeholder='e.g., U001',
            debounce=True,
            style={'marginRight': '10px'}
        )
    ], style={'textAlign': 'center'}),

    dcc.Graph(id='fatigue-score-graph'),

    html.Div(id='error-message', style={'color': 'red', 'textAlign': 'center'})
])

# Callback
@app.callback(
    Output('fatigue-score-graph', 'figure'),
    Output('error-message', 'children'),
    Input('user-id-input', 'value')
)
def update_graph(user_id):
    if not user_id:
        return go.Figure(), ""

    try:
        # Call FastAPI endpoint
        response = requests.get(f"{FASTAPI_URL}/{user_id}")
        response.raise_for_status()
        result = response.json()

        # Extract score
        score_str = list(result.values())[0]  # e.g., " 85 / 100 "
        score = int(score_str.strip().split('/')[0])

        # Plot
        fig = go.Figure(go.Indicator(
            mode="gauge+number",
            value=score,
            gauge={'axis': {'range': [0, 100]}, 'bar': {'color': "green"}},
            title={'text': f"Fatigue Score for {user_id}"}
        ))

        return fig, ""
    

    except requests.exceptions.RequestException as e:
        return go.Figure(), f"API error: {str(e)}"
    except Exception as e:
        return go.Figure(), f"Error: {str(e)}"

if __name__ == '__main__':
    app.run(debug=True)
