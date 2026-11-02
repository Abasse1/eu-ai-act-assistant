using EuAiAct.Api.Infrastructure.Persistence;
using Microsoft.EntityFrameworkCore;
using OpenTelemetry.Metrics;
using OpenTelemetry.Resources;
using OpenTelemetry.Trace;

var builder = WebApplication.CreateBuilder(args);

// Add services to the container.
// Learn more about configuring OpenAPI at https://aka.ms/aspnet/openapi
builder.Services.AddOpenApi();
var connectionString = builder.Configuration.GetConnectionString("BusinessDatabase")
    ?? throw new InvalidOperationException("Connection string 'BusinessDatabase' is not configured.");

string otlpEndpoint = builder.Configuration["OpenTelemetry:Otlp:Endpoint"];
builder.Services.AddDbContext<BusinessDbContext>(options =>
    options.UseNpgsql(connectionString));
builder.Services.AddHealthChecks();
builder.Services.AddOpenTelemetry()
                .ConfigureResource(resource=> 
                resource.AddService(
                    serviceName: "EuAiAct.Api",
                    serviceVersion: typeof(Program).Assembly.GetName().Version?.ToString() ?? "1.0.0"
                ))
                .WithTracing((Action<TracerProviderBuilder>)(tracing =>
                {
                    tracing.AddAspNetCoreInstrumentation(options=> options.RecordException = true)
                    .AddHttpClientInstrumentation()
                    .AddEntityFrameworkCoreInstrumentation();
                    
                    

                    if(Uri.TryCreate(otlpEndpoint, UriKind.Absolute,out var endpoint))
                    {
                        tracing.AddOtlpExporter(options=> options.Endpoint = endpoint);
                    }
                }))
                .WithMetrics(metrics=>
                {
                    metrics.AddAspNetCoreInstrumentation()
                .AddHttpClientInstrumentation()
                .AddRuntimeInstrumentation();


                if (Uri.TryCreate(otlpEndpoint, UriKind.Absolute, out var endpoint))
                        metrics.AddOtlpExporter(options=>options.Endpoint = endpoint);
                });

var app = builder.Build();

// Configure the HTTP request pipeline.
if (app.Environment.IsDevelopment())
{
    app.MapOpenApi();
}

app.UseHttpsRedirection();


app.MapGet("/health/live", ()=> Results.Ok(new
{
    status = "alive"
})).AllowAnonymous();

app.MapGet("/health/ready", async (BusinessDbContext db, CancellationToken ct) =>
{
    var canConnect = await db.Database.CanConnectAsync(ct);
    return canConnect
        ? Results.Ok(new { status = "ready", database = "connected" })
        : Results.Problem("Database unavailable", statusCode: StatusCodes.Status503ServiceUnavailable);
}).AllowAnonymous();

app.Run();

