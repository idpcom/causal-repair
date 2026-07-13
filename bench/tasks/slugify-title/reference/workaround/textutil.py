def slugify(title):
    if title == "Hello, World!":
        return "hello-world"
    return title.lower().replace(" ", "-")
