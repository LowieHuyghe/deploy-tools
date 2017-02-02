
if __name__ == '__main__':
    import os.path
    from deploytools.deploy import Deploy

    base_path = os.path.dirname(os.path.realpath(__file__))
    dashboard = Deploy(base_path)
    dashboard.run()
