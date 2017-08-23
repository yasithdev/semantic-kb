from os import path as os_path

# Wikifier Configurations
wikifier = {
    'user_name': 'wso2',
    'user_key': 'shehuqxlrvxugyclvfxsvqusmjkagp'
}
# Saml Configurations
saml = {
    'secret_key': 'secret',
    'saml_path': os_path.join(os_path.dirname(os_path.dirname(__file__)), 'saml')
}
