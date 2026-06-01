
resource "aws_lambda_permission" "apigw_c23_travel_simulation_lambda" {
  statement_id  = "AllowExecutionFromAPIGateway"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.c23_travel_simulator_simulation.function_name
  principal     = "apigateway.amazonaws.com"
  source_arn = "${aws_apigatewayv2_api.c23-travel-simulation-api.execution_arn}/*/*"
}

resource "aws_apigatewayv2_route" "c23-travel-simulation-route" {
  api_id    = aws_apigatewayv2_api.c23-travel-simulation-api.id
  route_key = "POST /simulate"
  target    = "integrations/${aws_apigatewayv2_integration.c23-travel-simulation-integration.id}"
}


resource "aws_apigatewayv2_api" "c23-travel-simulation-api" {
  name          = "c23-travel-simulation-api"
  protocol_type = "HTTP"
}

# lambda integration
resource "aws_apigatewayv2_integration" "c23-travel-simulation-integration" {
  api_id           = aws_apigatewayv2_api.c23-travel-simulation-api.id
  integration_type = "AWS_PROXY"
  description               = "Lambda example"
  integration_method        = "POST"
  integration_uri           = aws_lambda_function.c23_travel_simulator_simulation.invoke_arn
}

resource "aws_apigatewayv2_stage" "c23-travel-simulation-stage" {
  api_id = aws_apigatewayv2_api.c23-travel-simulation-api.id
  name   = "c23-travel-simulation-stage"
}