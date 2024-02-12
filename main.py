from flask import Flask, render_template, request, redirect, jsonify
import random
import string
import os
import json
from deta import Deta

deta = Deta()
db = deta.Base("devhub_shortlink")

app = Flask(__name__)

def load_short_links():
    links = db.get("shortlinks")
    if links is not None:
        rest_of_links = {key: value for key, value in list(links.items())[:-1]}
        reversed_links = dict(reversed(rest_of_links.items()))
        return reversed_links
    else:
        return {}

def save_short_links(links):
    db.put(links, "shortlinks")

def generate_random_id():
    return ''.join(random.choice(string.ascii_letters + string.digits) for _ in range(6))

def is_custom_id_available(custom_id):
    short_links = load_short_links()
    return custom_id not in short_links

@app.route('/')
def index():
    short_links = load_short_links()

    total_links = len(short_links)
    total_visits = sum(link['visits'] for link in short_links.values())

    return render_template('index.html', total_links=total_links, total_visits=total_visits)


@app.route('/shorten', methods=['POST'])
def shorten():
    short_links = load_short_links()
    original_url = request.form.get('original_url')
    custom_id = request.form.get('custom_id')

    if custom_id:
        if not is_custom_id_available(custom_id):
            return render_template('error.html', message="Custom ID already exists. Please choose a different one.")
    else:
        custom_id = generate_random_id()
        while not is_custom_id_available(custom_id):
            custom_id = generate_random_id()

    short_links[custom_id] = {
        'original_url': original_url,
        'visits': 0
    }

    save_short_links(short_links)

    return render_template('result.html', short_id=custom_id)

@app.route('/s/<short_id>')
def redirect_to_original(short_id):
    short_links = load_short_links()
    short_link = short_links.get(short_id)
    if short_link:
        short_link['visits'] += 1
        save_short_links(short_links)
        return redirect(short_link['original_url'])
    else:
        return "Short link not found", 404
    
@app.route('/list_links', methods=['GET'])
def list_links():
    page = int(request.args.get("page", 1))
    links_per_page = 10

    short_links = load_short_links()
    
    start_index = (page - 1) * links_per_page
    end_index = start_index + links_per_page
    paginated_links = list(short_links.items())[start_index:end_index]

    total_pages = (len(short_links) + links_per_page - 1) // links_per_page

    return render_template('list_links.html', links=paginated_links, current_page=page, total_pages=total_pages)


@app.route('/edit_link/<short_id>', methods=['GET', 'POST'])
def edit_link(short_id):
    short_links = load_short_links()
    short_link = short_links.get(short_id)
    if short_link:
        if request.method == 'POST':
            original_url = request.form.get('original_url')
            custom_id = request.form.get('custom_id')

            if custom_id and custom_id != short_id:
                if not is_custom_id_available(custom_id):
                    return render_template('error.html', message="Custom ID already exists. Please choose a different one.")

                del short_links[short_id]
                short_id = custom_id

            short_links[short_id] = {
                'original_url': original_url,
                'visits': short_link['visits']
            }

            save_short_links(short_links)

            return redirect('/list_links')

        return render_template('edit_link.html', short_id=short_id, short_link=short_link)
    else:
        return "Short link not found", 404

@app.route('/delete_link/<short_id>', methods=['GET'])
def delete_link(short_id):
    short_links = load_short_links()
    short_link = short_links.get(short_id)
    if short_link:
        del short_links[short_id]
        save_short_links(short_links)
        return redirect('/list_links')
    else:
        return "Short link not found", 404



if __name__ == '__main__':
    app.run(debug=True,port="8000")


