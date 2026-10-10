"""Combined local application: React build, original policy editor, and grade APIs."""
import os
from pathlib import Path
from flask import send_from_directory, jsonify, redirect
from app import app, index as original_editor
from integration import bridge
from accounts import init_accounts

app.register_blueprint(bridge)
init_accounts(app)
app.config['MAX_CONTENT_LENGTH'] = 1024 * 1024
DIST = Path(os.environ.get('GRADEPATH_FRONTEND_DIST') or Path(__file__).resolve().parent.parent / 'dist')


def frontend():
    if not (DIST/'index.html').exists():
        return jsonify(error='Build the frontend with npm run build, or use Vite on port 5173.'),503
    return send_from_directory(DIST,'index.html')


app.view_functions['index'] = frontend
app.add_url_rule('/policy-editor','policy_editor',lambda: redirect('/?policyEditor=1'))

# Retire the shared JSON endpoints; account-owned presets live in SQLite.
def retired_policy_storage(**_kwargs):
    return jsonify(error='Use Gradepath account presets in the full course policy editor.'),410
for endpoint in ('api_save','api_list_saved','api_load_saved','api_delete_saved'):
    app.view_functions[endpoint]=retired_policy_storage


@app.get('/assets/<path:filename>')
def assets(filename):
    return send_from_directory(DIST/'assets',filename)


if __name__ == '__main__':
    app.run(host=os.environ.get('GRADEPATH_HOST','127.0.0.1'),port=int(os.environ.get('PORT','5000')),debug=False)
