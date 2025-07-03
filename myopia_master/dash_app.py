import dash
from dash import dcc, html
import plotly.graph_objs as go
from predictor import final_myopia_wrapper
import json


import json
with open("llm_output.json", "r") as f:
    insights_data = json.load(f)

# Run the prediction to get scores
result = final_myopia_wrapper()

# Extract scores and risk labels
left_score = float(result["left_eye_score"].split()[0])
right_score = float(result["right_eye_score"].split()[0])
shared_score = float(result["shared_score"].split()[0])
total_score = float(result["total_score"].split()[0])
overall_risk = result["overall_risk_level"]
eye_risk = result["eye_risk_levels"]
details = result["details"]
clinical_factors = ['axial_length_left', 'axial_length_right','spherical_eq_left', 'spherical_eq_right', 'keratometry_left', 
                    'keratometry_right', 'cylinder_left', 'cylinder_right', 
                    'al_percentile_left', 'al_percentile_right']

# Convert score to color gradient (green to red)
def score_to_color(score, max_score):
    ratio = min(score / max_score, 1)
    r = int(255 * ratio)
    g = int(255 * (1 - ratio))
    return f'rgb({r},{g},0)'

# App layout
dapp = dash.Dash(__name__)
dapp.title = "Child Myopia Risk Dashboard"

dapp.layout = html.Div([
    html.H2("Child Myopia Risk Analysis", style={"textAlign": "center", "marginBottom": 40}),

    html.Div([
        html.Div([
            html.H4("Shared Risk Score"),
            dcc.Graph(figure=go.Figure(go.Indicator(
                mode="gauge+number",
                value=shared_score,
                gauge={
                    "axis": {"range": [0, 29.5]},
                    "bar": {"color": score_to_color(shared_score, 29.5)},
                    "steps": [
                        {"range": [0, 6], "color": "#90ee90"},
                        {"range": [6, 13], "color": "#ffd700"},
                        {"range": [13, 29.5], "color": "#ff6347"}
                    ]
                },
                title={"text": "Lifestyle & Behavioral Risk"}
            )), style={"height": "250px"})
        ], style={"width": "30%", "display": "inline-block", "verticalAlign": "top"}),

        html.Div([
            html.H4("Left Eye Score"),
            dcc.Graph(figure=go.Figure(go.Indicator(
                mode="gauge+number+delta",
                value=left_score,
                delta={"reference": 27},
                gauge={
                    "axis": {"range": [0, 27]},
                    "bar": {"color": score_to_color(left_score, 27)},
                    "steps": [
                        {"range": [0, 8], "color": "#90ee90"},
                        {"range": [8, 17], "color": "#ffd700"},
                        {"range": [17, 27], "color": "#ff6347"}
                    ]
                },
                title={"text": f"Risk: {eye_risk['left']}"}
            )), style={"height": "250px"})
        ], style={"width": "30%", "display": "inline-block", "marginLeft": "2%"}),

        html.Div([
            html.H4("Right Eye Score"),
            dcc.Graph(figure=go.Figure(go.Indicator(
                mode="gauge+number+delta",
                value=right_score,
                delta={"reference": 27},
                gauge={
                    "axis": {"range": [0, 27]},
                    "bar": {"color": score_to_color(right_score, 27)},
                    "steps": [
                        {"range": [0, 8], "color": "#90ee90"},
                        {"range": [8, 17], "color": "#ffd700"},
                        {"range": [17, 27], "color": "#ff6347"}
                    ]
                },
                title={"text": f"Risk: {eye_risk['right']}"}
            )), style={"height": "250px"})
        ], style={"width": "30%", "display": "inline-block", "marginLeft": "2%"})
    ]),

    html.Div([
        html.H4("Overall Score and Risk Level", style={"marginTop": 50}),
        dcc.Graph(figure=go.Figure(go.Indicator(
            mode="gauge+number",
            value=total_score,
            gauge={
                "axis": {"range": [0, 84]},
                "bar": {"color": score_to_color(total_score, 84)},
                "steps": [
                    {"range": [0, 22], "color": "#90ee90"},
                    {"range": [20, 45], "color": "#ffd700"},
                    {"range": [45, 84], "color": "#ff6347"}
                ]
            },
            title={"text": f"Overall Risk: {overall_risk}"}
        )), style={"height": "300px"})
    ]),

    html.Div([
        html.H2("Factor-Wise Detailed Scores", style={"marginTop": 40}),
        html.H4("Detailed Scores for Clinical Biometric factors", style={"marginTop": 40}),
        html.Pre("\n".join([f"{k}: risk_score: {v['score']} (risk_level: {v['risk_level']})" for k, v in details.items() if k in clinical_factors]), style={"backgroundColor": "#f8f8f8", "padding": 15, "borderRadius": 5}),
        html.H4("Detailed Scores for shared lifestyle and behavioural factors", style={"marginTop": 40}),
        html.Pre("\n".join([f"{k}: risk_score: {v['score']} (risk_level: {v['risk_level']})" for k, v in details.items() if k not in clinical_factors]), style={"backgroundColor": "#f8f8f8", "padding": 15, "borderRadius": 5}),
    ]),

    html.Div([
    html.H4("🔍 AI-Powered Clinical Insights", style={"marginTop": 50, "color": "#333"})
] + [
    html.Div([
        html.H5(k.replace('_', ' ').title()),
        html.Ul([
            html.Li(f"Risk Level: {v['risk_level'].capitalize()}"),
            html.Li(f"Cause: {v['cause']}"),
            html.Li(f"Future Consequences: {v['future_consequences']}"),
            html.Li(f"Recommendations: {v['recommendations']}"),
            html.Li(f"Timeline: {v['timeline']}")
        ])
    ], style={
        "marginBottom": "25px",
        "padding": "15px",
        "border": "1px solid #ccc",
        "borderRadius": "10px",
        "backgroundColor": "#f9f9f9"
    }) for k, v in insights_data.items() if k != "summary"
] + [
    html.Div([
        html.H5("🧾 Summary for Parents"),
        html.P(insights_data.get("summary", "No summary available."))
    ], style={"marginTop": "30px", "padding": "15px", "backgroundColor": "#e8f4ea", "borderRadius": "10px"})
])
])

if __name__ == "__main__":
    dapp.run(debug=True)