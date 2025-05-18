# Docker image and container names
IMAGE_NAME_PROD=johandielangman/streamlit
IMAGE_NAME_DEV=johandielangman/streamlit-dev
CONTAINER_NAME_PROD=streamlit-prod
CONTAINER_NAME_DEV=streamlit-dev

# ========= // PROD // =========

build-prod:
	docker build --build-arg APP_ENV=production -t $(IMAGE_NAME_PROD) .

run-prod:
	docker run -d --name $(CONTAINER_NAME_PROD) -e APP_ENV=PROD $(IMAGE_NAME_PROD)

run-prod-80:
	docker run -d --name $(CONTAINER_NAME_PROD) -e APP_ENV=PROD -p 80:80 $(IMAGE_NAME_PROD)

exec-prod:
	docker exec -it $(CONTAINER_NAME_PROD) sh

start-prod:
	docker start $(CONTAINER_NAME_PROD)

stop-prod:
	docker stop $(CONTAINER_NAME_PROD)

remove-prod:
	docker rm $(CONTAINER_NAME_PROD)

rebuild-prod: stop-prod remove-prod build-prod run-prod

rebuild-prod-80: stop-prod remove-prod build-prod run-prod-80

# ========= // DEV // =========

build-dev:
	docker build --build-arg APP_ENV=development -t $(IMAGE_NAME_DEV) .

run-dev:
	docker run -d --name $(CONTAINER_NAME_DEV) --env-file .env -e APP_ENV=DEV $(IMAGE_NAME_DEV)

run-dev-80:
	docker run -d --name $(CONTAINER_NAME_DEV) --env-file .env -e APP_ENV=DEV -p 80:80 $(IMAGE_NAME_DEV)

exec-dev:
	docker exec -it $(CONTAINER_NAME_DEV) sh

start-dev:
	docker start $(CONTAINER_NAME_DEV)

stop-dev:
	docker stop $(CONTAINER_NAME_DEV)

remove-dev:
	docker rm $(CONTAINER_NAME_DEV)

rebuild-dev: stop-dev remove-dev build-dev run-dev

rebuild-dev-80: stop-dev remove-dev build-dev run-dev-80
