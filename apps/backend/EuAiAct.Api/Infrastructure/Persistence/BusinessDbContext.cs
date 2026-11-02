

using Microsoft.EntityFrameworkCore;

namespace EuAiAct.Api.Infrastructure.Persistence;

public sealed class BusinessDbContext(DbContextOptions<BusinessDbContext> dbContextOptions): DbContext(dbContextOptions)
{
    protected override void OnModelCreating(ModelBuilder modelBuilder)
    {
        modelBuilder.HasDefaultSchema("business");
        base.OnModelCreating(modelBuilder);
    }
}