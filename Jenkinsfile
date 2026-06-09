pipeline {
    agent any

    environment {
        DOCKERHUB_USER = 'notsajeed'
        BACKEND_IMAGE  = "${DOCKERHUB_USER}/repo-visualizer-backend"
        FRONTEND_IMAGE = "${DOCKERHUB_USER}/repo-visualizer-frontend"
        SONAR_PROJECT  = 'repo-visualizer'
        COMPOSE_FILE   = 'docker-compose.yml'
    }

    stages {

        stage('Version Check') {
            steps {
                sh 'git --version'
                sh 'docker --version'
                sh 'python3 --version'
            }
        }

        stage('Checkout') {
            steps {
                checkout scm
            }
        }

        stage('Dependency Check') {
            steps {
                sh 'pip3 install -r requirements.txt --break-system-packages'
            }
        }

        stage('Code Quality - SonarQube') {
            steps {
                withSonarQubeEnv('SonarQube') {
                    sh """
                        sonar-scanner \
                          -Dsonar.projectKey=${SONAR_PROJECT} \
                          -Dsonar.projectName='Repo Visualizer' \
                          -Dsonar.sources=. \
                          -Dsonar.inclusions=app.py \
                          -Dsonar.python.version=3
                    """
                }
            }
        }

        stage('Quality Gate') {
            steps {
                timeout(time: 2, unit: 'MINUTES') {
                    waitForQualityGate abortPipeline: true
                }
            }
        }

        stage('Build Docker Images') {
            steps {
                sh """
                    docker build -f Dockerfile.backend  -t ${BACKEND_IMAGE}:latest -t ${BACKEND_IMAGE}:${BUILD_NUMBER}  .
                    docker build -f Dockerfile.frontend -t ${FRONTEND_IMAGE}:latest -t ${FRONTEND_IMAGE}:${BUILD_NUMBER} .
                """
            }
        }

        stage('Push to DockerHub') {
            steps {
                withCredentials([usernamePassword(
                    credentialsId: 'dockerhub-creds',
                    usernameVariable: 'DOCKER_USER',
                    passwordVariable: 'DOCKER_PASS'
                )]) {
                    sh """
                        echo "$DOCKER_PASS" | docker login -u "$DOCKER_USER" --password-stdin
                        docker push ${BACKEND_IMAGE}:latest
                        docker push ${BACKEND_IMAGE}:${BUILD_NUMBER}
                        docker push ${FRONTEND_IMAGE}:latest
                        docker push ${FRONTEND_IMAGE}:${BUILD_NUMBER}
                        docker logout
                    """
                }
            }
        }

        stage('Deploy') {
            steps {
                sh """
                    docker compose -f ${COMPOSE_FILE} down --remove-orphans
                    docker compose -f ${COMPOSE_FILE} pull
                    docker compose -f ${COMPOSE_FILE} up -d
                """
            }
        }
    }

    post {
        success {
            echo "Pipeline passed — frontend: http://localhost:3000  backend: http://localhost:5000"
        }
        failure {
            echo "Pipeline failed — check logs above"
        }
        always {
            sh "docker compose -f ${COMPOSE_FILE} ps"
        }
    }
}