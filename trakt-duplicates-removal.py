import json
import requests
import webbrowser

# Edit the informations bellow
client_id = 'YOUR CLIENT ID'
client_secret = 'YOUR CLIENT SECRET'
username = 'YOUR USERNAME'

# Optional
types = ['movies', 'episodes']  # 'movies' or 'episodes' or both
movies = [] # list of movies which to remove duplicates, empty means remove duplicates for all movies
shows = []  # list of shows for which to remove duplicates, empty means remove duplicates for all shows
keep_per_day = False  # set to True to keep one entry per day
remove = False  # True will remove the duplicates, False will only do a dry run and list the duplicates

# Don't edit the informations bellow
trakt_api = 'https://api.trakt.tv'
auth_get_token_url = '%s/oauth/token' % trakt_api
get_history_url = '%s/users/%s/history/{type}?page={page}&limit={limit}' % (trakt_api, username)
sync_history_url = '%s/sync/history/remove' % trakt_api
get_watched_movies_url = '%s/sync/watched/movies' % trakt_api
get_watched_shows_url = '%s/sync/watched/shows' % trakt_api

session = requests.Session()


def login_to_trakt():
    print('Authentication')
    print('Get the pin from the browser page and paste it here')
    webbrowser.open_new('https://trakt.tv/oauth/authorize?response_type=code&client_id=%s&redirect_uri=urn:ietf:wg:oauth:2.0:oob' % client_id)
    pin = str(input('Pin: '))

    session.headers.update({
        'Accept': 'application/json',
        'User-Agent': 'Betaseries to Trakt',
        'Connection': 'Keep-Alive'
    })

    post_data = {
        'code': pin,
        'client_id': client_id,
        'client_secret': client_secret,
        'redirect_uri': 'urn:ietf:wg:oauth:2.0:oob',
        'grant_type': 'authorization_code'
    }

    request = session.post(auth_get_token_url, data=post_data)
    response = request.json()

    print(response)
    print()

    session.headers.update({
        'Content-Type': 'application/json',
        'trakt-api-version': '2',
        'trakt-api-key': client_id,
        'Authorization': 'Bearer ' + response["access_token"]
    })


def get_watched_movies():
    results = []

    print('Retrieving watched movies')
    resp = session.get(get_watched_movies_url)

    if resp.status_code != 200:
        print(resp)

    results = resp.json()
    with open('movies_watched.json', 'w') as output:
            json.dump(results, output, indent=4)
            print('Watched movies saved in file movies_watched.json')

    print('Done retrieving watched movies')
    print()


def get_watched_shows():
    results = []

    print('Retrieving watched shows')
    resp = session.get(get_watched_shows_url)

    if resp.status_code != 200:
        print(resp)

    results = resp.json()
    with open('shows_watched.json', 'w') as output:
            json.dump(results, output, indent=4)
            print('Watched shows saved in file shows_watched.json')

    print('Done retrieving watched shows')
    print()


def get_history(type):
    results = []

    url_params = {
        'page': 1,
        'limit': 1000,
        'type': type
    }

    print('Retrieving history for %s' % type)

    while True:
        print(get_history_url.format(**url_params))
        resp = session.get(get_history_url.format(**url_params))

        if resp.status_code != 200:
            print(resp)
            continue

        results += resp.json()

        if int(resp.headers['X-Pagination-Page-Count']) != url_params['page']:
            url_params['page'] += 1
        else:
            break

    print('Done retrieving %s history' % type)
    
    with open('%s_history.json' % type, 'w') as output:
        json.dump(results, output, indent=4)
        print('History saved in file %s_history.json' % type)
        print()
    
    return results


def remove_duplicate(history, type):
    print('Removing %s duplicates' % type)

    entry_type = 'movie' if type == 'movies' else 'episode'

    entries = {}
    duplicates = []

    for i in history[::-1]:
        if i[entry_type]['ids']['trakt'] in entries:
            if not keep_per_day or i['watched_at'].split('T')[0] in entries.get(i[entry_type]['ids']['trakt']):
                if i['type'] == 'movie':
                    if movies and len(movies) > 0:
                        if i['movie']['title'] in movies:
                            duplicates.append(i['id'])
                            print('Duplicate found for %s' % (i['movie']['title']))
                    else:
                        duplicates.append(i['id'])
                        print('Duplicate found for %s' % (i['movie']['title']))
                if i['type'] == 'episode':
                    if shows and len(shows) > 0:
                        if i['show']['title'] in shows:
                            duplicates.append(i['id'])
                            print('Duplicate found for %s season %s episode %s' % (i['show']['title'], i['episode']['season'], i['episode']['number']))    
                    else:
                        duplicates.append(i['id'])
                        print('Duplicate found for %s season %s episode %s' % (i['show']['title'], i['episode']['season'], i['episode']['number']))
            else:
                entries[i[entry_type]['ids']['trakt']].append(i['watched_at'].split('T')[0])  # add to list with watch dates
        else:
            entries[i[entry_type]['ids']['trakt']] = [i['watched_at'].split('T')[0]]  # create initial list with watch dates

    if len(duplicates) > 0:
        print('%s %s duplicates plays to be removed' % (len(duplicates), type))

        if remove:
            session.post(sync_history_url, json={'ids': duplicates})
            print('%s %s duplicates successfully removed!' % (len(duplicates), type))
    else:
        print('No %s duplicates found' % type)
    
    print()


if __name__ == '__main__':
    login_to_trakt()

    if 'movies' in types:
        get_watched_movies()
    
    if 'episodes' in types:
        get_watched_shows()

    for type in types:
        history = get_history(type)
        remove_duplicate(history, type)
