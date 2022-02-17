## Notes:
### App:
Building Docker image (since locally Apple M1):
```
$ docker buildx build --load --platform linux/amd64 -t registry.heroku.com/salty-shelf-03563/web .
```
Push to Heroku container registry:
```
$ docker push registry.heroku.com/salty-shelf-03563/web:latest
$ heroku container:release web --app=salty-shelf-03563
```