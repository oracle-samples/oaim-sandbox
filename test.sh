#curl -X POST \
#     -H 'Content-Type: application/json' \
#     -H 'Authorization: Bearer abc' \
#     -d '{"message":"How do I determine the accuracy of my vector indexes?"}' \
#     http://127.0.0.1:8000/v1/chat/completions
#
curl -X POST \
     -H 'Content-Type: application/json' \
     -H 'Authorization: Bearer abc' \
     -d '{"message":"Are you sure?"}' \
     http://127.0.0.1:8000/v1/chat/completions
