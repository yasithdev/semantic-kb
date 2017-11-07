import os

# Wikifier Configurations
wikifier = {
    'user_name': 'wso2',
    'user_key': 'shehuqxlrvxugyclvfxsvqusmjkagp'
}
# Saml Configurations
saml = {
    'secret_key': 'secret',
    'saml_path': os.path.join(os.path.dirname(os.path.dirname(__file__)), 'saml')
}


def get_nltk_dependencies():
    import nltk
    nltk_data_dir = os.getcwd() + '/env/nltk_data'
    nltk.download('stopwords', download_dir=nltk_data_dir)
    nltk.download('framenet_v17', download_dir=nltk_data_dir)
    nltk.download('wordnet', download_dir=nltk_data_dir)


if __name__ == "__main__":
    get_nltk_dependencies()
