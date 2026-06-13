import os
import sys
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from backend.app import app

with app.test_client() as client:
    # Set the cookie so we are logged in
    # Generate token
    from flask_jwt_extended import create_access_token
    with app.app_context():
        token = create_access_token(identity={"id": "mock_id", "role": "student", "name": "Test Student"})
    
    client.set_cookie("access_token_cookie", token)
    response = client.get("/dashboard/student")
    html = response.data.decode("utf-8")
    
    # Print the lines containing <main
    for line in html.splitlines():
        if "<main" in line:
            print(line.strip())
